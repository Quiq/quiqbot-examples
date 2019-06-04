const ngrok = require('ngrok');

(async () => {
  const ngrokUrl = await ngrok.connect({
    proto: 'http',
    addr: 3000,
    subdomain: process.env.ngrokAuthToken,
    authtoken: process.env.ngrokSubdomain,
    region: 'us',
  });

  console.log(`
*****  Put the following as your user's "Bot URL" -- ${ngrokUrl}/handler  *****
*****  Put the following as your user's "Bot URL" -- ${ngrokUrl}/handler  *****
*****  Put the following as your user's "Bot URL" -- ${ngrokUrl}/handler  *****
*****  Put the following as your user's "Bot URL" -- ${ngrokUrl}/handler  *****
*****  Put the following as your user's "Bot URL" -- ${ngrokUrl}/handler  *****
  `);
  process.stdin.resume();
})();
