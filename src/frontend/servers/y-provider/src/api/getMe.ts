import axios, { AxiosRequestConfig } from 'axios';
import { IncomingHttpHeaders } from 'http';

import { COLLABORATION_BACKEND_BASE_URL } from '@/env';

import { getCookieValue } from '../helpers';

export interface User {
  id: string;
  email: string;
  full_name: string;
  short_name: string;
  language: string;
}

export const getMe = async (requestHeaders: IncomingHttpHeaders): Promise<User> => {

  const jwtToken = getCookieValue(requestHeaders.cookie, 'token');
  const axiosHeaders: Record<string, string> = {};
  if (requestHeaders.origin && typeof requestHeaders.origin === 'string') {
    axiosHeaders['Origin'] = requestHeaders.origin;
  }

  if (jwtToken) {
    axiosHeaders['Authorization'] = `Bearer ${jwtToken}`;
  }

  const axiosConfig: AxiosRequestConfig = {
    headers: axiosHeaders,
  };

  
  const response = await axios.get<User>(
    `${COLLABORATION_BACKEND_BASE_URL}/api/v1.0/users/me/`,
    axiosConfig,
  );

  if (response.status !== 200) {
    throw new Error(`Failed to fetch user: ${response.statusText}`);
  }

  return response.data;
};
