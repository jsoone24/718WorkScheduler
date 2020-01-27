import Time_Scheduler
import Work_Scheduler
import constants
import copy

Timetable = copy.deepcopy(constants.Timetable)
is_weekend = copy.deepcopy(constants.is_weekend)
which_group = copy.deepcopy(constants.which_group)
work_group = copy.deepcopy(constants.work_group)
p2 = copy.deepcopy(constants.p2)


scheduled_work, real_worker, outing = Time_Scheduler.scheduler(Timetable, which_group, work_group, is_weekend, p2)
result = Work_Scheduler. schedule_place(real_worker, outing)

for h in result:
    print(h.name, end=' ')
    Work_Scheduler.whatis_hwork(h.work)