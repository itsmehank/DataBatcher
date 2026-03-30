-- ---------------------------------------------------------------------------
-- 1. 원천 거래 데이터 (수집)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rh_trade_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sggCd VARCHAR(10) COMMENT '시군구 코드 (예: 11650=서초구)',
    umdNm VARCHAR(100) COMMENT '읍면동명',
    mhouseNm VARCHAR(100) COMMENT '연립다세대 명칭',
    jibun VARCHAR(50) COMMENT '지번',
    buildYear INT COMMENT '건축년도',
    excluUseAr DECIMAL(10, 4) COMMENT '전용면적(㎡)',
    landAr DECIMAL(10, 4) COMMENT '대지권면적(㎡)',
    dealYear INT COMMENT '거래년도',
    dealMonth INT COMMENT '거래월',
    dealDay INT COMMENT '거래일',
    dealAmount BIGINT COMMENT '거래금액(만원)',
    floor INT COMMENT '층 (양수=지상, 음수=지하)',
    dealingGbn VARCHAR(20) COMMENT '거래유형',
    estateAgentSggNm VARCHAR(100) COMMENT '중개사무소 소재지',
    rgstDate VARCHAR(8) COMMENT '등기일자',
    slerGbn VARCHAR(20) COMMENT '매도자구분',
    buyerGbn VARCHAR(20) COMMENT '매수자구분',
    price_per_pyeong DECIMAL(20, 2) COMMENT '전용면적 평당가',
    land_price_per_pyeong DECIMAL(20, 2) COMMENT '대지권 평당가',
    land_share_ratio DECIMAL(10, 4) COMMENT '대지권면적 / 전용면적 비율',
    UNIQUE KEY unique_trade (sggCd, jibun, dealYear, dealMonth, dealDay, dealAmount, mhouseNm, excluUseAr),
    INDEX idx_sgg_umd (sggCd, umdNm)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='연립다세대 매매 실거래 원천 데이터';

-- ---------------------------------------------------------------------------
-- 3. 수집 로그
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_ingestion_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lawd_cd VARCHAR(10) NOT NULL COMMENT '법정동 코드',
    deal_ymd VARCHAR(6) NOT NULL COMMENT '거래년월 (YYYYMM)',
    status VARCHAR(20) DEFAULT 'SUCCESS' COMMENT '수집 결과',
    record_count INT DEFAULT 0 COMMENT '수집 건수',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_lawd_deal_ymd (lawd_cd, deal_ymd)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='데이터 수집 작업 로그';

-- ---------------------------------------------------------------------------
-- 4. 동단위 월분석
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS monthly_dong_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sggCd VARCHAR(10) NOT NULL COMMENT '시군구 코드',
    umdNm VARCHAR(100) NOT NULL COMMENT '읍면동명',
    deal_ymd VARCHAR(6) NOT NULL COMMENT '거래년월 (YYYYMM)',

    total_avg_price_per_pyeong DECIMAL(20, 2) COMMENT '전체 평균 평당 단가',
    total_avg_land_price_per_pyeong DECIMAL(20, 2) COMMENT '전체 평균 대지 평당 단가',
    total_trade_count INT COMMENT '전체 거래 건수',
    low_floor_trade_ratio DECIMAL(5, 4) COMMENT '전체 거래 대비 저층(1층 미만) 거래 비율',
    direct_trade_count INT COMMENT '직거래 건수',
    ind_to_corp_trade_count INT COMMENT '개인 매도 & 법인 매수 거래 건수',
    high_floor_avg_price_per_pyeong DECIMAL(20, 2) COMMENT '1층 이상 평균 평당 단가',
    high_floor_avg_land_price_per_pyeong DECIMAL(20, 2) COMMENT '1층 이상 평균 대지 평당 단가',
    high_floor_trade_count INT COMMENT '1층 이상 거래 건수',
    low_floor_avg_price_per_pyeong DECIMAL(20, 2) COMMENT '1층 미만 평균 평당 단가',
    low_floor_avg_land_price_per_pyeong DECIMAL(20, 2) COMMENT '1층 미만 평균 대지 평당 단가',
    low_floor_trade_count INT COMMENT '1층 미만 거래 건수',

    price_change_rate_vs_prev DECIMAL(10, 4) COMMENT '직전 거래월 대비 평당가 변동률 (%)',
    months_since_prev_trade INT COMMENT '직전 거래월과의 개월 차',
    avg_monthly_volume_cumulative DECIMAL(10, 2) COMMENT '해당 월 직전까지의 누적 월평균 거래량',
    volume_change_rate_vs_avg DECIMAL(10, 4) COMMENT '누적 평균 거래량 대비 현재 거래량 비율 (%)',
    price_per_pyeong_stddev DECIMAL(20, 2) COMMENT '현재 월 평당 단가 표준편차',
    is_low_volume BOOLEAN COMMENT '거래량 5건 미만 여부',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sgg_umd_ymd (sggCd, umdNm, deal_ymd)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='월별 동단위 연립다세대 거래 분석 요약';

-- ---------------------------------------------------------------------------
-- 5. 동단위 분석 로그
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analysis_log_dong (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sggCd VARCHAR(10) NOT NULL,
    umdNm VARCHAR(100) NOT NULL,
    deal_ymd VARCHAR(6) NOT NULL,
    status VARCHAR(20) DEFAULT 'SUCCESS',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sgg_umd_ymd_log (sggCd, umdNm, deal_ymd),
    INDEX idx_sgg_umd (sggCd, umdNm) COMMENT '분석 조회용 복합 인덱스'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='동단위 분석 작업 로그';

-- ---------------------------------------------------------------------------
-- 6. 건물단위 지상층 분석
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS building_transaction_analysis_above_ground (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sggCd VARCHAR(10) NOT NULL COMMENT '법정동 코드',
    umdNm VARCHAR(100) COMMENT '동이름',
    jibun VARCHAR(50) NOT NULL COMMENT '지번',
    buildYear INT NOT NULL COMMENT '건축년도',
    mhouseNm VARCHAR(100) COMMENT '연립다세대명',
    deal_ymd VARCHAR(6) NOT NULL COMMENT '거래년월',
    trade_count INT COMMENT '해당 월의 거래 건수',
    avg_dealAmount BIGINT COMMENT '평균 거래 대금 (만원)',

    avg_exclu_price_per_pyeong DECIMAL(20, 2) COMMENT '평균 전용면적 평당 단가',
    prev_avg_exclu_price_per_pyeong DECIMAL(20, 2) COMMENT '직전 거래월의 평균 전용면적 평당 단가',
    exclu_price_change_rate_vs_prev DECIMAL(10, 4) COMMENT '직전 거래월 대비 전용면적 평당가 변동률 (%)',

    avg_land_price_per_pyeong DECIMAL(20, 2) COMMENT '평균 대지권 평당 단가',
    prev_avg_land_price_per_pyeong DECIMAL(20, 2) COMMENT '직전 거래월의 평균 대지권 평당 단가',
    land_price_change_rate_vs_prev DECIMAL(10, 4) COMMENT '직전 거래월 대비 대지권 평당가 변동률 (%)',

    months_since_prev_trade INT COMMENT '직전 거래월과의 개월 차',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sgg_jibun_buildyear_ymd (sggCd, jibun, buildYear, deal_ymd),
    INDEX idx_sgg_jibun_buildyear (sggCd, jibun, buildYear)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='월별 건물단위(지번+건축년도) 지상층 연립다세대 거래 분석';

-- ---------------------------------------------------------------------------
-- 7. 건물단위 지상층 분석 로그
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analysis_log_building_above_ground (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sggCd VARCHAR(10) NOT NULL,
    jibun VARCHAR(50) NOT NULL,
    buildYear INT NOT NULL,
    status VARCHAR(20) DEFAULT 'SUCCESS',
    last_processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sgg_jibun_buildyear_log (sggCd, jibun, buildYear)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='지상층 건물단위(지번+건축년도) 분석 작업 로그';

-- ---------------------------------------------------------------------------
-- 8. 건물단위 지하층 분석
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS building_transaction_analysis_below_ground (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sggCd VARCHAR(10) NOT NULL COMMENT '법정동 코드',
    umdNm VARCHAR(100) COMMENT '동이름',
    jibun VARCHAR(50) NOT NULL COMMENT '지번',
    buildYear INT NOT NULL COMMENT '건축년도',
    mhouseNm VARCHAR(100) COMMENT '연립다세대명',
    deal_ymd VARCHAR(6) NOT NULL COMMENT '거래년월',
    trade_count INT COMMENT '해당 월의 거래 건수',
    avg_dealAmount BIGINT COMMENT '평균 거래 대금 (만원)',

    avg_exclu_price_per_pyeong DECIMAL(20, 2) COMMENT '평균 전용면적 평당 단가',
    prev_avg_exclu_price_per_pyeong DECIMAL(20, 2) COMMENT '직전 거래월의 평균 전용면적 평당 단가',
    exclu_price_change_rate_vs_prev DECIMAL(10, 4) COMMENT '직전 거래월 대비 전용면적 평당가 변동률 (%)',

    avg_land_price_per_pyeong DECIMAL(20, 2) COMMENT '평균 대지권 평당 단가',
    prev_avg_land_price_per_pyeong DECIMAL(20, 2) COMMENT '직전 거래월의 평균 대지권 평당 단가',
    land_price_change_rate_vs_prev DECIMAL(10, 4) COMMENT '직전 거래월 대비 대지권 평당가 변동률 (%)',

    months_since_prev_trade INT COMMENT '직전 거래월과의 개월 차',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sgg_jibun_buildyear_ymd (sggCd, jibun, buildYear, deal_ymd),
    INDEX idx_sgg_jibun_buildyear (sggCd, jibun, buildYear)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='월별 건물단위(지번+건축년도) 지하층 연립다세대 거래 분석';

-- ---------------------------------------------------------------------------
-- 9. 건물단위 지하층 분석 로그
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analysis_log_building_below_ground (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sggCd VARCHAR(10) NOT NULL,
    jibun VARCHAR(50) NOT NULL,
    buildYear INT NOT NULL,
    status VARCHAR(20) DEFAULT 'SUCCESS',
    last_processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sgg_jibun_buildyear_log (sggCd, jibun, buildYear)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='지하층 건물단위(지번+건축년도) 분석 작업 로그';

-- ---------------------------------------------------------------------------
-- 10. 스키마 버전 관리
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_version (
    version_key VARCHAR(100) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='스키마 버전 추적';

INSERT INTO schema_version (version_key)
VALUES ('2026-03-19-init-schema-sql')
ON DUPLICATE KEY UPDATE applied_at = CURRENT_TIMESTAMP;
