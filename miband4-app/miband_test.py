from staze import Test, App, HttpClient, parsing
from werkzeug.test import TestResponse

from app.sensor import Sensor


class TestApiMiband(Test):
    pass
    # Disabled: Not working
    # def test_get(self, app: App, http: HttpClient):
    #     with app.app_context():
    #         response: TestResponse = http.get('/sensors/pulse', 200)

    #         json: dict = parsing.parse(response.json, dict)

    #         sensor: Sensor = Sensor(**json['sensor'])
    #         assert 50 <= sensor.value <= 130
