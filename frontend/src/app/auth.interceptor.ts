import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError } from 'rxjs/operators';
import { throwError } from 'rxjs';

import { clearStoredSession, getStoredSession } from './session';

const SKIP_AUTH_REDIRECT_HEADER = 'X-Skip-Auth-Redirect';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const token = getStoredSession()?.accessToken?.trim();

  const skipAuthRedirect = req.headers.get(SKIP_AUTH_REDIRECT_HEADER) === 'true';
  const request = !token || req.headers.has('Authorization')
    ? req
    : req.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`,
        },
      });

  return next(request).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        clearStoredSession();
        if (!skipAuthRedirect && router.url !== '/login') {
          router.navigateByUrl('/login');
        }
      }

      return throwError(() => error);
    }),
  );
};
