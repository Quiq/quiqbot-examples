To get started, you will need to get your bot user set up.  Follow the instructions [here](https://developers.goquiq.com/docs/bots#/?id=mountain-bot-deflection-amp-escalation) to get started.  Once you get to the spot where you need to add the Bot URL you can proceed.

### Notes
- If you don't use ngrok, you can ignore this. This example utilizes [ngrok](https://ngrok.com/) to expose a local port over https so your Quiq site can access it.  If you have a paid account for Ngrok, you can set the `ngrokSubdomain` environment variable to the ngrok subdomain you use, and the `ngrokAuthToken` to the auth token with your ngrok license.  This is not required for the example, however without it, whenever you reset ngrok, you will need to update the bot URL in the Quiq Admin-UI Settings.
- This example also utilizes [nodemon](https://nodemon.io/) to automatically reload your server whenever you save your changes. This will not restart the ngrok server, as it does not need to be reset on every change.

### Instructions
1. After cloning the repository, run `npm install`.  If you do not have node installed, you will first need to [download it](https://nodejs.org/en/) 
2. You will need to set some environment variabels for this demo to work.  These variables can be retrieved from your Bot User Settings in the Quiq Admin Interface.  You can do so by adding the lines to your `~/.bash_profile`, swapping out the placeholders with your variables
   1. `export appId="Your Bot Public API Id"`
   2. `export appSecret="Your Bot Public API Secret"`
   3. `export site="https://yoursite.goquiq.com"`
   4. `export hookSecret=""Your Bot Webhook Secret"`
3. run `npm start`.  This will start the server, as well as give you the URL you will need as your Bot URL

You should now be able to have your bot handle any conversations that are routed to it.  Ensure you have it set to online and available so it's ready to receive conversations.