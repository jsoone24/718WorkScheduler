
import random

# 오늘 무슨 조인지
#start_2020_01_01_B = datetime.datetime(2020, 1, 1)  # 1월 1일 근무조
#today = datetime.datetime(2020, 2, 13)  # 오늘 날짜
#which_group = ((today - start_2020_01_01_B).days + 1) % 3  # 나머지 0이면 A, 1이면 B, 2이면 C
which_group = -1
work_group = {0: 'A', 1: 'B', 2: 'C'}  # workgroup 에 which_group을 대입하면 오늘 무슨 조인지 문자로 파악 가능
#is_weekend = int(today.weekday() / 5) + 1  # 오늘 주말인지 아닌지 1이면 평일, 2이면 주말

is_weekend = 0
placeA = [[2, 2, 2, 1], [5, 3, 2, 1], [3, 2, 2, 1], [2, 2, 1, 1]]  # 정출, 별정, 별후, 서남문 순서
placeB = [[5, 3, 2, 1], [5, 3, 2, 1], [2, 2, 1, 1], [2, 2, 1, 1]]
placeC = [[5, 3, 2, 1], [5, 3, 2, 1], [5, 3, 2, 1], [2, 2, 1, 1]]

placeA_weekend = [[2, 2, 1, 1], [3, 2, 2, 1], [2, 2, 2, 1], [2, 2, 1, 1]]
placeB_weekend = [[3, 2, 2, 1], [3, 2, 2, 1], [2, 2, 1, 1], [2, 2, 1, 1]]
placeC_weekend = [[3, 2, 2, 1], [3, 2, 2, 1], [2, 2, 2, 1], [2, 2, 1, 1]]

placetable = [[placeA, placeA_weekend],
              [placeB, placeB_weekend],
              [placeC, placeC_weekend]]

# 근무 시간, 타수
TimeA = [6, 4, 8, 12]
WorkA = [sum(x) for x in placeA]
WorkA_weekend = [sum(x) for x in placeA_weekend]

TimeB = [8, 12, 2, 4]
WorkB = [sum(x) for x in placeB]
WorkB_weekend = [sum(x) for x in placeB_weekend]

TimeC = [10, 2, 6, 22]
WorkC = [sum(x) for x in placeC]
WorkC_weekend = [sum(x) for x in placeC_weekend]

Timetable = [[TimeA, WorkA, WorkA_weekend],
             [TimeB, WorkB, WorkB_weekend],
             [TimeC, WorkC, WorkC_weekend]]  # 배열로 묶어서 저장


# 선호 근무 조사
class fav:
    def __init__(self, name, t3=[], t2=[]):
        self.name = name
        self.times3 = {'A': t3[0], 'B': t3[1], 'C': t3[2]}
        self.times2 = {'A': t2[0], 'B': t2[1], 'C': t2[2]}
        self.wheres_he = [0, 0, 0, 0]
        self.work = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
        self.flag = 0

    def __str__(self):
        return self.name


# 2분대 사람들 공백 차례로 1, 2, 3, 4분대
a1 = fav('Member01', [[6, 4, 8], [8, 12, 4], [10, 6, 22]], [[6, 8], [8, 4], [2, 22]])
a2 = fav('Member02', [[6, 4, 8], [8, 12, 2], [10, 2, 6]], [[4, 8], [8, 2], [10, 2]])
a3 = fav('Member03', [[6, 4, 8], [8, 12, 4], [2, 6, 22]], [[6, 8], [8, 4], [2, 22]])
a4 = fav('Member04', [[6, 4, 8], [8, 12, 2], [10, 2, 6]], [[6, 4], [8, 2], [10, 2]])
a5 = fav('Member05', [[6, 8, 12], [8, 12, 2], [10, 6, 22]], [[6, 8], [12, 2], [6, 22]])

a6 = fav('Member06', [[6, 4, 8], [8, 12, 2], [10, 2, 6]], [[6, 8], [8, 2], [10, 6]])
a7 = fav('Member07', [[6, 4, 8], [8, 12, 4], [10, 2, 6]], [[6, 4], [8, 4], [10, 2]])
a8 = fav('Member08', [[6, 8, 12], [8, 12, 4], [2, 6, 22]], [[6, 8], [12, 4], [2, 22]])
a9 = fav('Member09', [[6, 4, 8], [8, 12, 2], [10, 2, 6]], [[6, 4], [8, 2], [6, 22]])
a10 = fav('Member10', [[6, 4, 8], [8, 12, 2], [10, 2, 6]], [[6, 4], [8, 2], [10, 2]])

a11 = fav('Member11', [[6, 4, 8], [8, 12, 2], [10, 2, 22]], [[6, 8], [8, 2], [10, 22]])
a12 = fav('Member12', [[6, 4, 8], [8, 12, 2], [10, 2, 6]], [[6, 4], [8, 2], [10, 2]])
a13 = fav('Member13', [[6, 8, 12], [8, 12, 4], [2, 6, 22]], [[8, 12], [12, 2], [2, 22]])
a14 = fav('Member14', [[6, 4, 8], [8, 12, 2], [10, 2, 6]], [[6, 4], [8, 2], [10, 2]])
a15 = fav('Member15', [[6, 4, 8], [8, 12, 2], [10, 2, 6]], [[6, 4], [8, 2], [10, 2]])
a16 = fav('Member16', [[6, 4, 8], [8, 12, 2], [10, 2, 6]], [[6, 4], [8, 2], [10, 2]])

a17 = fav('Member17', [[6, 4, 8], [8, 12, 2], [10, 2, 6]], [[6, 4], [12, 2], [10, 2]])
a18 = fav('Member18', [[6, 4, 8], [8, 12, 2], [10, 2, 6]], [[6, 4], [8, 2], [10, 2]])
a19 = fav('Member19', [[6, 4, 8], [8, 12, 2], [10, 2, 6]], [[4, 8], [8, 2], [10, 2]])
a20 = fav('Member20', [[6, 4, 8], [8, 12, 2], [10, 2, 22]], [[6, 8], [12, 2], [10, 2]])
a21 = fav('Member21', [[6, 4, 8], [8, 12, 2], [10, 2, 22]], [[6, 8], [8, 2], [6, 22]])

bundae = [5, 5, 6, 5]
p2 = [a1, a2, a3, a4, a5,
      a6, a7, a8, a9, a10, a11,
      a12, a13, a14, a15, a16,
      a17, a18, a19, a20, a21]

# 외출자, 사고자 입력
acci = []
out = []


def whos_out(p2, today_group, max_work):
    # acci = input("사고자 입력 : ").split()
    # out = input("외출자 입력 : ").split()
    global acci
    global out
    #acci = ['Member02', 'Member14', 'Member07', 'Member10']  # input("사고자 입력 : ").split()
    #out = ['Member17', 'Member11', 'Member18', 'Member01', 'Member08']  # ("외출자 입력 : ").split()

    real_worker, accident, outing, no_return_work, raw_outing = [], [], [], [], []

    for member in p2:
        if member.name in acci:
            accident.append(member)
        if member.name in out:
            outing.append(member)
            raw_outing.append(member)
    for member in p2:
        if (member not in accident) and (member not in outing):
            real_worker.append(member)

    if today_group != 'B' and (max_work[3] - len(outing)) < 0:  # 외출자 수가 막타 수 보다 많을 때
        for i in range(abs(max_work[3] - len(outing))):  # 막타자 수에서 외출자 수 빼고 그 사람 수 만큼 복귀타 없는 외출자 랜덤 선정
            lucky_man = random.choice(outing)
            outing.remove(lucky_man)
            no_return_work.append(lucky_man)
        for poor_man in outing:
            poor_man.wheres_he[3] = 1
    elif today_group == 'B' and max_work[2] + max_work[3] - len(outing) < 0:
        for i in range(abs(max_work[2] + max_work[3] - len(outing))):
            lucky_man = random.choice(outing)
            outing.remove(lucky_man)
            no_return_work.append(lucky_man)
        for poor_man in outing:
            poor_man.wheres_he[3] = 1
    else:  # 위 경우 둘다 해당하지 않을 때는 외출자는 막타 픽스
        for i in outing:
            i.wheres_he[3] = 1

    return real_worker, outing, accident, no_return_work, raw_outing  # 외출, 사고 없는 실 근무자, 외출자, 사고자
