import {
  All,
  Body,
  Controller,
  Get,
  HttpCode,
  Post,
  Req,
  Res,
} from '@nestjs/common';
import {
  ApiBearerAuth,
  ApiBody,
  ApiExcludeEndpoint,
  ApiOkResponse,
  ApiOperation,
  ApiTags,
} from '@nestjs/swagger';
import type { Request, Response } from 'express';

import { GatewayService } from './gateway.service';

@ApiTags('Gateway REST')
@Controller()
export class GatewayController {
  constructor(private readonly gatewayService: GatewayService) {}

  @Get('health')
  @ApiOperation({ summary: 'Estado local del gateway NestJS' })
  @ApiOkResponse({
    description: 'El gateway NestJS respondió correctamente.',
    schema: {
      example: {
        service: 'backend-nest-gateway',
        status: 'ok',
      },
    },
  })
  getHealth(): { service: string; status: 'ok' } {
    return {
      service: 'backend-nest-gateway',
      status: 'ok',
    };
  }

  @All('api/health')
  @ApiOperation({ summary: 'Proxy REST hacia el health del Core Service' })
  @ApiOkResponse({
    description: 'Respuesta del health interno de FastAPI.',
    schema: {
      example: {
        status: 'ok',
        environment: 'development',
        database: 'connected',
      },
    },
  })
  proxyApiHealth(@Req() req: Request, @Res() res: Response): Promise<void> {
    return this.gatewayService.proxy(req, res, '/api/health');
  }

  @Post('api/auth/login')
  @ApiOperation({ summary: 'Proxy REST hacia el login del Core Service' })
  @ApiBody({
    schema: {
      type: 'object',
      required: ['email', 'password', 'account_type'],
      properties: {
        email: { type: 'string', example: 'administrador@acb.com' },
        password: { type: 'string', example: '123ppp+++' },
        account_type: { type: 'string', example: 'admin' },
      },
    },
  })
  @ApiOkResponse({
    description: 'Respuesta del login del backend legado.',
    schema: {
      example: {
        id: 0,
        email: 'administrador@acb.com',
        role: 'admin',
        access_token: 'jwt-token',
        token_type: 'Bearer',
      },
    },
  })
  proxyLogin(@Req() req: Request, @Res() res: Response, @Body() _body: unknown): Promise<void> {
    return this.gatewayService.proxy(req, res, '/api/auth/login');
  }

  @Get('api/emergencias')
  @ApiBearerAuth('bearer')
  @ApiOperation({ summary: 'Proxy REST hacia emergencias' })
  @ApiOkResponse({ description: 'Lista de emergencias entregada por FastAPI.' })
  proxyEmergencias(@Req() req: Request, @Res() res: Response): Promise<void> {
    return this.gatewayService.proxy(req, res, '/api/emergencias');
  }

  @Get('api/clientes')
  @ApiBearerAuth('bearer')
  @ApiOperation({ summary: 'Proxy REST hacia clientes' })
  @ApiOkResponse({ description: 'Lista de clientes entregada por FastAPI.' })
  proxyClientes(@Req() req: Request, @Res() res: Response): Promise<void> {
    return this.gatewayService.proxy(req, res, '/api/clientes');
  }

  @Get('api/mecanicos')
  @ApiBearerAuth('bearer')
  @ApiOperation({ summary: 'Proxy REST hacia mecánicos' })
  @ApiOkResponse({ description: 'Lista de mecánicos entregada por FastAPI.' })
  proxyMecanicos(@Req() req: Request, @Res() res: Response): Promise<void> {
    return this.gatewayService.proxy(req, res, '/api/mecanicos');
  }

  @Get('api/sucursales')
  @ApiBearerAuth('bearer')
  @ApiOperation({ summary: 'Proxy REST hacia sucursales' })
  @ApiOkResponse({ description: 'Lista de sucursales entregada por FastAPI.' })
  proxySucursales(@Req() req: Request, @Res() res: Response): Promise<void> {
    return this.gatewayService.proxy(req, res, '/api/sucursales');
  }

  @All('api/graphql')
  @ApiExcludeEndpoint()
  @HttpCode(200)
  proxyApiGraphql(@Req() req: Request, @Res() res: Response): Promise<void> {
    return this.gatewayService.proxy(req, res, '/api/graphql');
  }

  @All('graphql')
  @ApiExcludeEndpoint()
  @HttpCode(200)
  proxyGraphql(@Req() req: Request, @Res() res: Response, @Body() _body: unknown): Promise<void> {
    return this.gatewayService.proxy(req, res, '/api/graphql');
  }

  @All('uploads/:path*')
  @ApiExcludeEndpoint()
  proxyUploads(@Req() req: Request, @Res() res: Response): Promise<void> {
    return this.gatewayService.proxy(req, res, req.originalUrl.split('?')[0]);
  }

  @All('api/:path*')
  @ApiExcludeEndpoint()
  proxyApi(@Req() req: Request, @Res() res: Response): Promise<void> {
    return this.gatewayService.proxy(req, res, req.originalUrl.split('?')[0]);
  }
}
