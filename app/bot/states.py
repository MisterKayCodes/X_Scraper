from aiogram.fsm.state import State, StatesGroup

class HarvestStates(StatesGroup):
    awaiting_x_target = State()
    awaiting_ig_target = State()
    awaiting_yt_url = State()
    awaiting_yt_limit = State()
    awaiting_channel_id = State()
    awaiting_harvest_limit = State()
    awaiting_max_duration = State()
    awaiting_new_source = State()
    awaiting_autocheck_setup = State()
    
class TargetCRUDStates(StatesGroup):
    awaiting_new_x_target = State()
    awaiting_new_ig_target = State()
    awaiting_new_yt_target = State()
