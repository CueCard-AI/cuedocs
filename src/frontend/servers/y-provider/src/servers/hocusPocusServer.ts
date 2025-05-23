import { Server } from '@hocuspocus/server';
import { validate as uuidValidate, version as uuidVersion } from 'uuid';

import { fetchDocument } from '@/api/getDoc';
import { getMe } from '@/api/getMe';
import { logger } from '@/utils';

export const hocusPocusServer = Server.configure({
  name: 'docs-collaboration',
  timeout: 30000,
  quiet: true,
  async onConnect({
    requestHeaders,
    connection,
    documentName,
    requestParameters,
    context,
    request,
  }) {
    const roomParam = requestParameters.get('room');

    if (documentName !== roomParam) {
      logger(
        'Invalid room name - Probable hacking attempt:',
        documentName,
        requestParameters.get('room'),
      );
      logger('UA:', request.headers['user-agent']);
      logger('URL:', request.url);

      return Promise.reject(new Error('Wrong room name: Unauthorized'));
    }

    if (!uuidValidate(documentName) || uuidVersion(documentName) !== 4) {
      logger('Room name is not a valid uuid:', documentName);

      return Promise.reject(new Error('Wrong room name: Unauthorized'));
    }

    let can_edit = false;

    try {
      const document = await fetchDocument(documentName, requestHeaders);

      if (!document.abilities.retrieve) {
        logger(
          'onConnect: Unauthorized to retrieve this document',
          documentName,
        );
        return Promise.reject(new Error('Wrong abilities:Unauthorized'));
      }

      can_edit = document.abilities.update;
  } catch (error: unknown) {
        console.error('[DEBUG] onConnect: Original error object caught:', error); // Use console.error for visibility
        if (error instanceof Error) {
          console.error('[DEBUG] onConnect: backend error message:', error.message);
          if (error.stack) {
            console.error('[DEBUG] onConnect: backend error stack:', error.stack);
          }
        } else {
          console.error('[DEBUG] onConnect: Caught error is NOT an instance of Error. Type:', typeof error, 'Value:', error);
        }
        // The following line creates the error message you ARE seeing logged by Hocuspocus/Node
        return Promise.reject(new Error('Backend error message: Unauthorized'));
      }

    connection.readOnly = !can_edit;

    /*
     * Unauthenticated users can be allowed to connect
     * so we flag only authenticated users
     */
    try {
      const user = await getMe(requestHeaders);
      // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
      context.userId = user.id;
    } catch (error: unknown) {
        console.error('[DEBUG] onConnect: Original error object caught:', error); // Use console.error for visibility
        if (error instanceof Error) {
          console.error('[DEBUG] onConnect: backend error message:', error.message);
          if (error.stack) {
            console.error('[DEBUG] onConnect: backend error stack:', error.stack);
          }
        } else {
          console.error('[DEBUG] onConnect: Caught error is NOT an instance of Error. Type:', typeof error, 'Value:', error);
        }
      }

    logger(
      'Connection established on room:',
      documentName,
      'canEdit:',
      can_edit,
    );
    return Promise.resolve();
  },
});
