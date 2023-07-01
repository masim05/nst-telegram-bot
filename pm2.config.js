module.exports = {
  apps : [
      {
        name: "NST telegram bot",
        script: "./app.py",
        watch: true,
        interpreter: "python",
        env: {
          "IMAGE_SIZE": "256",
          "EPOCHS": "500",
          "LR": "0.005",
          "ALPHA": "10",
          "BETA": "60",
          "TG_BOT_TOKEN":"",
        }
      }
  ]
}