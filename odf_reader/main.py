from view import ODFReaderView
from controller import ODFReaderController

if __name__ == "__main__":
    app = ODFReaderView()
    controller = ODFReaderController(app)
    app.set_controller(controller)
    app.mainloop()