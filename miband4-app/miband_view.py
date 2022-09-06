from staze import View

from app.miband.miband_service import MibandService


class PulseView(View):
    ROUTE: str = '/pulse'

    def get(self):
        return MibandService.instance().get_pulse().api_dict
