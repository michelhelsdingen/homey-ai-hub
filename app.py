"""Homey AI Hub — main application entry point."""
from homey import app as homey_app


class App(homey_app.App):
    async def on_init(self) -> None:
        self.log("Homey AI Hub starting...")


homey_export = App
