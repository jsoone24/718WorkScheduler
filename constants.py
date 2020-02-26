import random

# 오늘 무슨 조인지
#start_2020_01_01_B = datetime.datetime(2020, 1, 1)  # 1월 1일 근무조
#today = datetime.datetime(2020, 2, 13)  # 오늘 날짜
#which_group = ((today - start_2020_01_01_B).days + 1) % 3  # 나머지 0이면 A, 1이면 B, 2이면 C
which_group = -1
work_group = {0: 'A', 1: 'B', 2: 'C'}  # workgroup 에 which_group을 대입하면 오늘 무슨 조인지 문자로 파악 가능
#is_weekend = int(today.weekday() / 5) + 1  # 오늘 주말인지 아닌지 1이면 평일, 2이면 주말
is_weekend = 0


# 근무 타수 계산 1
# 정출, 별정, 별후, 서남문 순서
placeA = []
placeB = []
placeC = []
placeA_weekend = []
placeB_weekend = []
placeC_weekend = []

placetable = [[placeA, placeA_weekend],
              [placeB, placeB_weekend],
              [placeC, placeC_weekend]]


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


# 2소대 사람들 공백 차례로 1, 2, 3, 4분대
p2=[]
with open('Fav_work.txt', 'r', encoding='UTF8') as file:
    Flag=0
    count=0
    for line in file.readlines():
        if line[0]=="-":
            Flag=1
        elif line[0]!='#' and line[0].isdecimal()!=True and Flag==0:
            line = line.strip().split()
            p2.append(fav(line[0],[list(map(int,x.split(','))) for x in line[1:4]],[list(map(int,x.split(','))) for x in line[4:7]]))
        elif line[0]!='#' and Flag==1 and count<6:
            line = line.strip().split()
            placetable[int(count%3)][int(count/3)]=[list(map(int,x.split(','))) for x in line[1:5]]
            count+=1

#근무 타수 계산 2
TimeA = [6, 4, 8, 12]
WorkA = [sum(x) for x in placetable[0][0]]
WorkA_weekend = [sum(x) for x in placetable[0][1]]

TimeB = [8, 12, 2, 4]
WorkB = [sum(x) for x in placetable[1][0]]
WorkB_weekend = [sum(x) for x in placetable[1][1]]

TimeC = [10, 2, 6, 22]
WorkC = [sum(x) for x in placetable[2][0]]
WorkC_weekend = [sum(x) for x in placetable[2][1]]

Timetable = [[TimeA, WorkA, WorkA_weekend],
             [TimeB, WorkB, WorkB_weekend],
             [TimeC, WorkC, WorkC_weekend]]  # 배열로 묶어서 저장

# 외출자, 사고자 입력
acci = []
out = []


def whos_out(p2, today_group, max_work):
    global acci
    global out

    # acci = ['Member05','Member11','Member17','Member13']  # input("사고자 입력 : ").split()
    # out = []  # ("외출자 입력 : ").split()

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