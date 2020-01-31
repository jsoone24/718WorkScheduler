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
print("실근무자")
for member in real_worker:
    print(member.name, member.wheres_he)
print("외출자 복귀타")
for member in outing:
    print(member.name, member.wheres_he)
print('temp_work들어간 사람')
c = []
for a in scheduled_work:
    for b in a:
        if b not in c:
            c.append(b)
            print(b.name, b.wheres_he)
print(len(c))

result = Work_Scheduler. schedule_place(real_worker, outing)

for h in result:
    print(h.name, end=' ')
    Work_Scheduler.whatis_hwork(h.work)