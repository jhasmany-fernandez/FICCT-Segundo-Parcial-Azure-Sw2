import { Injectable } from '@nestjs/common';
import type { Request, Response } from 'express';

@Injectable()
export class GatewayService {
  private readonly fastApiBaseUrl = (process.env.FASTAPI_BASE_URL || 'http://core-service:8000').replace(/\/$/, '');

  async proxy(req: Request, res: Response, upstreamPath: string): Promise<void> {
    const query = req.originalUrl.includes('?') ? req.originalUrl.slice(req.originalUrl.indexOf('?')) : '';
    const url = `${this.fastApiBaseUrl}${upstreamPath}${query}`;
    const response = await fetch(url, {
      method: req.method,
      headers: this.buildUpstreamHeaders(req),
      body: this.buildBody(req),
    });

    const buffer = Buffer.from(await response.arrayBuffer());
    res.status(response.status);
    this.copyResponseHeaders(response, res);
    res.send(buffer);
  }

  private buildUpstreamHeaders(req: Request): Headers {
    const headers = new Headers();

    for (const [key, value] of Object.entries(req.headers)) {
      if (!value) {
        continue;
      }
      if (['host', 'connection', 'content-length'].includes(key.toLowerCase())) {
        continue;
      }

      if (Array.isArray(value)) {
        headers.set(key, value.join(', '));
      } else {
        headers.set(key, value);
      }
    }

    return headers;
  }

  private buildBody(req: Request): BodyInit | undefined {
    if (req.method === 'GET' || req.method === 'HEAD') {
      return undefined;
    }

    if (Buffer.isBuffer(req.body)) {
      return new Uint8Array(req.body);
    }

    if (typeof req.body === 'string') {
      return req.body;
    }

    if (req.body === undefined || req.body === null) {
      return undefined;
    }

    return JSON.stringify(req.body);
  }

  private copyResponseHeaders(response: globalThis.Response, res: Response): void {
    response.headers.forEach((value, key) => {
      if (['content-length', 'transfer-encoding', 'connection'].includes(key.toLowerCase())) {
        return;
      }
      res.setHeader(key, value);
    });
  }
}
