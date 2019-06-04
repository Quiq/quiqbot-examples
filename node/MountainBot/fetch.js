const nodeFetch = require('node-fetch');
const logger = require('node-color-log');

const fetch = async (path, options) => {
  const method = options.method || 'GET';
  const body = options.body;
  const responseType = 'none';

  try {
    logger.color('blue').log(`${new Date()} ${method} ${path} ${JSON.stringify(body)}`);

    const res = await nodeFetch(`${process.env.site}/${path}`, {
      method,
      body: body ? JSON.stringify(body) : undefined,
      cache: 'no-cache',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Basic ${Buffer.from(
          `${process.env.appId}:${process.env.appSecret}`,
          'binary',
        ).toString('base64')}`,
      },
    });

    logger
      .color(res.status >= 400 ? 'red' : 'green')
      .log(`${new Date()} ${method} ${path} ${res.status} ${res.message || ''}`);

    if (res.status >= 400) {
      throw new Error(res.message);
    }

    if (responseType === 'json') return await res.json();

    return;
  } catch (e) {
    throw new Error(e.message);
  }
};

module.exports = fetch;
