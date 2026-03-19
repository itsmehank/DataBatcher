import { NestFactory } from '@nestjs/core';
import * as cookieParser from 'cookie-parser';
import helmet from 'helmet';
import { AppModule } from './app.module';

function parseCorsOrigins(): string[] | true {
  const raw = process.env.CORS_ORIGIN;
  if (!raw || raw === '*') {
    return true;
  }
  return raw.split(',').map((o) => o.trim()).filter(Boolean);
}

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.setGlobalPrefix('api');

  app.use(cookieParser());
  app.use(helmet());

  const origin = parseCorsOrigins();
  app.enableCors({ origin, credentials: true });

  const port = Number(process.env.BACKEND_PORT || 4000);
  await app.listen(port);
}

bootstrap();
