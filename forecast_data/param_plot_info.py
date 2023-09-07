"""
This class resolves the information pertaining
to different parameters regarding plots
"""


class ParamInfo:

    def __init__(self, param_name) -> None:
        self.param_name = param_name

    def resolve_param(self):
        if 'temperature' in self.param_name:
            self.cname = "winter"
            self.levels = [-10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
            self.ext = "both"
            self.min_val = -10.0
            self.max_val = 50.0
            self.unit_label = '°C'
        elif 'rainfall' in self.param_name:
            self.cname = "Spectral_r"
            self.levels = [1, 5, 10, 15, 20, 30, 50, 75, 100, 150, 200, 250]
            self.ext = "max"
            self.min_val = 1.0
            self.max_val = 250.0
            self.unit_label = "mm"
        elif 'humidity' in self.param_name:
            self.cname = "summer_r"
            self.levels = [10, 15, 20, 30, 40, 50, 60, 70, 80, 90]
            self.ext = "both"
            self.min_val = 10.0
            self.max_val = 90.0
            self.unit_label = "%"
        elif 'wind' in self.param_name:
            self.cname = "cividis_r"
            self.levels = [1, 5, 10, 15, 20, 30, 50, 75, 100]
            self.ext = "max"
            self.min_val = None
            self.max_val = None
            self.unit_label = "kmph"

