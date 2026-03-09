GCP 상에서 관리 포인트(VM 운영, OS 패치 등)를 최소화하고, 확장성과 안정성을 확보할 수 있는 아키텍처를 제안해 드립니다.

기존에 고려하셨던 "VM에 DB와 파이썬 스크립트를 모두 올리는 방식"은 말씀하신 대로 관리 비용이 높습니다. 대신 **Fully Managed Service(완전 관리형 서비스)**를 조합하는 방식이 가장 적합합니다.

### 추천 아키텍처: Cloud SQL + Cloud Run Jobs + Cloud Scheduler

이 구조는 서버를 직접 관리할 필요가 없으며(Serverless), DB 백업 및 장애 복구, 배치 작업의 스케줄링과 알림 처리가 매우 간편해집니다.

#### 1. 데이터베이스: Cloud SQL for MySQL
로컬 Docker로 띄우던 MySQL을 대체합니다.
- **장점**:
  - OS 설치, 패치, DB 백업, 복제 등을 구글이 알아서 관리해줍니다.
  - 저장 용량을 자동으로 늘려주는 기능(Storage Auto-increase)이 있어, 200GB에서 시작해 500GB까지 데이터가 늘어나도 별도 조치 없이 운영 가능합니다.
- **설정**:
  - `MySQL 8.0` 버전을 선택합니다.
  - 데이터가 200GB 수준이므로 `Enterprise` 에디션이나 `Standard` 머신 타입을 사용하는 것이 성능상 안전합니다. (초기 비용 절감을 원하면 낮은 사양으로 시작 후 클릭 한 번으로 사양 업그레이드 가능)

#### 2. 배치 실행 환경: Cloud Run Jobs
파이썬 적재 스크립트(`.py`)를 실행할 환경입니다.
- **장점**:
  - **Serverless**: 코드가 실행되는 동안에만 비용이 발생합니다. (VM처럼 24시간 켜둘 필요 없음)
  - **컨테이너 기반**: 로컬에서 Docker로 패키징한 환경 그대로 클라우드에서 실행되므로 "내 컴퓨터에선 되는데 서버에선 안 되는" 문제가 없습니다.
  - **긴 실행 시간**: 일반적인 Cloud Run(웹 서비스용)과 달리, Job은 최대 24시간까지 실행 가능하므로 대용량 적재 작업에 적합합니다.

#### 3. 스케줄링: Cloud Scheduler
Crontab을 대체합니다.
- **기능**: 정해진 시간(예: 매일 16:30)에 Cloud Run Jobs를 트리거합니다.
- **관리**: GCP 콘솔 웹 화면에서 스케줄을 쉽게 수정하거나, "지금 실행" 버튼으로 즉시 테스트해볼 수 있습니다.

#### 4. 모니터링 및 알람: Cloud Monitoring
- **알람 설정**: Cloud Run Job이 실패(Exit Code가 0이 아님)했을 때, 자동으로 이메일이나 슬랙으로 알람을 보내도록 "로그 기반 알람(Log-based Alert)"을 쉽게 설정할 수 있습니다.

---

### 마이그레이션 단계별 가이드

제안한 구조로 옮기기 위해 필요한 작업을 정리해 드립니다.

#### 1단계: 프로젝트 컨테이너화 (Dockerfile 작성)
현재 프로젝트 루트에 `Dockerfile`을 생성하여 파이썬 실행 환경을 정의해야 합니다. `requirements.txt`를 기반으로 아래와 같이 작성할 수 있습니다.

```dockerfile
# Dockerfile
FROM python:3.10-slim

# 시스템 의존성 설치 (MySQL 클라이언트 등)
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 기본 실행 명령어 (Cloud Run Job 생성 시 덮어쓸 수 있음)
CMD ["python", "scripts/daily_update.py"]
```

#### 2단계: 데이터베이스 이관
1. 로컬 MySQL 데이터를 `mysqldump`로 백업 (`.sql` 파일 생성).
2. 생성된 파일을 Google Cloud Storage(GCS) 버킷에 업로드.
3. GCP 콘솔의 Cloud SQL 메뉴에서 "가져오기(Import)" 기능을 사용해 GCS에 있는 덤프 파일을 Cloud SQL로 적재.

#### 3단계: Cloud Run Job 배포
1. `Dockerfile`을 빌드하여 Google Artifact Registry에 이미지를 업로드합니다.
2. **Cloud Run Jobs**를 생성합니다.
   - **Daily Job**: `python scripts/daily_update.py` 명령어로 실행되도록 설정.
   - **Weekly Job**: `python scripts/weekly_update.py` 명령어로 실행되도록 설정(이미지는 동일한 것 사용).
3. **환경 변수 설정**: `DATABASE_URL` 환경 변수에 Cloud SQL 접속 정보를 입력합니다.
   - 프로젝트 코드(`core/config_loader.py`)가 이미 `DATABASE_URL` 환경 변수를 우선적으로 읽도록 잘 작성되어 있어, 코드 수정 없이 설정만으로 연결 가능합니다.

#### 4단계: 스케줄러 등록
- Cloud Scheduler 메뉴에서 각 Job을 트리거할 크론(Cron) 식(예: `30 16 * * 1-5`)을 등록합니다.

### 요약
VM을 직접 관리하는 대신 **Cloud SQL**과 **Cloud Run Jobs**를 사용하면, **운영 관리 포인트는 줄이면서(NoOps)** 원하는 **자동화와 안정성**을 모두 얻을 수 있습니다. 또한 `Config` 코드가 이미 환경 변수를 지원하도록 잘 짜여 있어, 코드 수정은 거의 없이 `Dockerfile` 추가만으로 이전이 가능해 보입니다.