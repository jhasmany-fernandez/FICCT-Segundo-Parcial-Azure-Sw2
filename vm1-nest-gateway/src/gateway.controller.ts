import {
  Body,
  Controller,
  Get,
  Headers,
  HttpException,
  HttpStatus,
  Post,
} from '@nestjs/common';

import { GatewayService } from './gateway.service';

@Controller()
export class GatewayController {
  constructor(private readonly gatewayService: GatewayService) {}

  @Get('health')
  getHealth(): { service: string; status: 'ok' } {
    return {
      service: 'vm1-nest-gateway',
      status: 'ok',
    };
  }

  @Get('gateway/status')
  async getGatewayStatus(): Promise<{ vm1: 'ok'; vm2: 'ok' }> {
    try {
      return await this.gatewayService.getStatus();
    } catch (error) {
      throw this.mapError(error, 'No se pudo verificar el estado de VM2.');
    }
  }

  @Get('gateway/emergencias')
  async getEmergencias(@Headers('authorization') authorization?: string): Promise<unknown> {
    try {
      return await this.gatewayService.proxyEmergencias(authorization);
    } catch (error) {
      throw this.mapError(error, 'No se pudo consultar /api/emergencias en VM2.');
    }
  }

  @Post('gateway/graphql')
  async postGraphql(
    @Body() body: unknown,
    @Headers('authorization') authorization?: string,
  ): Promise<unknown> {
    try {
      return await this.gatewayService.proxyGraphql(body, authorization);
    } catch (error) {
      throw this.mapError(error, 'No se pudo consultar /graphql en VM2.');
    }
  }

  private mapError(error: unknown, fallback: string): HttpException {
    const message = error instanceof Error && error.message.trim() ? error.message : fallback;
    return new HttpException(
      {
        service: 'vm1-nest-gateway',
        status: 'error',
        message,
      },
      HttpStatus.BAD_GATEWAY,
    );
  }
}
