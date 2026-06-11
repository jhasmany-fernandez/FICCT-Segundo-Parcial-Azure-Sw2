import { Injectable } from '@nestjs/common';

@Injectable()
export class GatewayService {
  private readonly vm2BaseUrl = process.env.VM2_BASE_URL || 'http://34.122.37.25';
  private readonly vm2ApiUrl = process.env.VM2_API_URL || `${this.vm2BaseUrl}/api`;
  private readonly vm2GraphqlUrl = process.env.VM2_GRAPHQL_URL || `${this.vm2BaseUrl}/graphql`;

  async getStatus(): Promise<{ vm1: 'ok'; vm2: 'ok' }> {
    const response = await fetch(`${this.vm2ApiUrl}/health`);

    if (!response.ok) {
      throw new Error(`VM2 health check failed with status ${response.status}`);
    }

    return {
      vm1: 'ok',
      vm2: 'ok',
    };
  }

  async proxyEmergencias(authorization?: string): Promise<unknown> {
    const response = await fetch(`${this.vm2ApiUrl}/emergencias`, {
      headers: this.buildForwardHeaders(authorization),
    });

    return this.parseProxyResponse(response);
  }

  async proxyGraphql(body: unknown, authorization?: string): Promise<unknown> {
    const response = await fetch(this.vm2GraphqlUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.buildForwardHeaders(authorization),
      },
      body: JSON.stringify(body ?? {}),
    });

    return this.parseProxyResponse(response);
  }

  private buildForwardHeaders(authorization?: string): Record<string, string> {
    if (!authorization?.trim()) {
      return {};
    }

    return {
      Authorization: authorization,
    };
  }

  private async parseProxyResponse(response: Response): Promise<unknown> {
    const text = await response.text();
    const payload = this.safeJsonParse(text);

    if (!response.ok) {
      throw new Error(
        typeof payload === 'object' && payload !== null && 'detail' in payload
          ? String((payload as { detail?: unknown }).detail)
          : `Upstream request failed with status ${response.status}`,
      );
    }

    return payload;
  }

  private safeJsonParse(text: string): unknown {
    if (!text.trim()) {
      return {};
    }

    try {
      return JSON.parse(text) as unknown;
    } catch {
      return { raw: text };
    }
  }
}
