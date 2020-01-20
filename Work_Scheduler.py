import random
import copy
# 오늘 무슨 조인지
import datetime

start_2020_01_01_B = datetime.datetime(2020, 1, 1)  # 1월 1일 근무조
today = datetime.datetime(2020, 1, 13)  # 오늘 날짜
which_group = ((today - start_2020_01_01_B).days + 1) % 3  # 나머지 0이면 A, 1이면 B, 2이면 C
work_group = {0: 'A', 1: 'B', 2: 'C'}  # workgroup 에 which_group을 대입하면 오늘 무슨 조인지 문자로 파악 가능
is_weekend = int(today.weekday() / 5) + 1  # 오늘 주말인지 아닌지 1이면 평일, 2이면 주말

# 근무 시간, 타수
TimeA = [6, 4, 8, 12]
WorkA = [7, 11, 8, 6]
WorkA_weekend = [6, 8, 8, 6]

TimeB = [8, 12, 2, 4]
WorkB = [11, 11, 6, 6]
WorkB_weekend = [8, 8, 6, 6]

TimeC = [10, 2, 6, 22]
WorkC = [11, 11, 11, 6]
WorkC_weekend = [8, 8, 8, 6]

Timetable = [[TimeA, WorkA, WorkA_weekend],
             [TimeB, WorkB, WorkB_weekend],
             [TimeC, WorkC, WorkC_weekend]]  # 배열로 묶어서 저장

placeA = [[2, 2, 2, 1], [5, 3, 2, 1], [3, 2, 2, 1], [2, 2, 1, 1]]  # 정출, 별정, 별후, 서남문 순서
placeB = [[5, 3, 2, 1], [5, 3, 2, 1], [2, 2, 1, 1], [2, 2, 1, 1]]
placeC = [[5, 3, 2, 1], [5, 3, 2, 1], [5, 3, 2, 1], [2, 2, 1, 1]]

placeA_weekend = [[2, 2, 1, 1], [3, 2, 2, 1], [2, 2, 2, 1], [2, 2, 1, 1]]
placeB_weekend = [[3, 2, 2, 1], [3, 3, 2, 1], [2, 2, 2, 1], [2, 2, 1, 1]]
placeC_weekend = [[3, 2, 2, 1], [3, 2, 2, 1], [2, 2, 2, 1], [2, 2, 1, 1]]

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

p2 = [a1, a2, a3, a4, a5, a6, a7, a8,
      a9, a10, a11, a12, a13, a14, a15,
      a16, a17, a18, a19, a20, a21]


# 외출자, 사고자 입력, 실 근무자 계산
def whos_out(p2):
    acci = ['Member01','Member06','Member21','Member14','Member17','Member11','Member10','Member08']#input("사고자 입력 : ").split()
    out = ['Member11'] #("외출자 입력 : ").split()
    real_worker, accident, outing = [], [], []
    for member in p2:
        if member.name in acci:
            accident.append(member)
        if member.name in out:
            outing.append(member)
    for member in p2:
        if (member not in accident) and (member not in outing):
            real_worker.append(member)

    return real_worker, outing, accident #외출, 사고 없는 실 근무자, 외출자, 사고자


# 긴밤자 결정
def whos_long_night(hes_2, temp_work, long_night_size):
    long_nighter = []
    for __ in range(long_night_size):
        while True:
            chosen = random.choice(hes_2)
            if chosen not in long_nighter:
                temp_work[0].append(chosen)
                temp_work[1].append(chosen)
                chosen.wheres_he[0] = 1
                chosen.wheres_he[1] = 1
                long_nighter.append(chosen)
                break

    return temp_work, long_nighter


# 3타자 입력,계산
def whos_3_2(real_worker, outing, today_group, accident, temp_work, max_work):
    real_worker_size = len(real_worker)  # 현원(총원 - 외출자 - 사고자)
    size_2 = real_worker_size * 3 - sum(max_work) + len(outing)  # 2타자 수
    size_3 = real_worker_size - size_2  # 3타자 수
    no_return_work = []  # 복귀타 없는 외출자

    if today_group != 'B' and (max_work[3] - len(outing)) < 0:  # 외출자 수가 막타 수 보다 많을 때
        for i in range(abs(max_work[3] - len(outing))):
            lucky_man = random.choice(outing)
            outing.remove(lucky_man)
            accident.append(lucky_man)
            no_return_work.append(lucky_man)
        for poor_man in outing:
            poor_man.wheres_he[3] = 1
    elif today_group == 'B' and max_work[2] + max_work[3] - len(outing) < 0:
        for i in range(abs(max_work[2] + max_work[3] - len(outing))):
            lucky_man = random.choice(outing)
            outing.remove(lucky_man)
            accident.append(lucky_man)
            no_return_work.append(lucky_man)
        for poor_man in outing:
            poor_man.wheres_he[3] = 1

    else: #위 경우 둘다 해당하지 않을 때는 외출자는 막타 픽스
        for i in outing:
            i.wheres_he[3] = 1


    if is_weekend == 2: #주말에는 size_2가 2타자 +복귀타 없는 외출자로 계산되서 빼줌
        size_2 -= len(no_return_work)
        size_3 = real_worker_size - size_2

    if today_group != 'B':
        max_work[3] = max_work[3] - len(outing)
    else:
        temp_work[3] = outing

    hes_3, hes_2, long_nighter = [], [], []

    if size_2 > 0 and is_weekend == 1:  # 2타자 자동 계산
        start_2 = 'Member12' #input("2타 시작 입력 : ")
        for member in real_worker:
            if member.name == start_2:
                index = real_worker.index(member)
                for i in range(size_2):
                    hes_2.append(real_worker[(i + index) % real_worker_size])
                break

    elif size_2 > 0 and is_weekend == 2:  # 주말 2타자 랜덤 추첨
        temp = []
        for i in range(size_2):
            lucky_man = random.choice(real_worker)
            temp.append(lucky_man)
            real_worker.remove(lucky_man)
            hes_2.append(lucky_man)
        real_worker += temp

    for member in real_worker:
        if member not in hes_2:
            hes_3.append(member)

    if today_group == 'B':
        long_night_size = real_worker_size - max_work[2] - max_work[3] + len(outing)  # 긴밤자 수
        if long_night_size > 0:
            temp_work, long_nighter = whos_long_night(hes_2, temp_work, long_night_size)
        print("긴밤자 수 : %d" % long_night_size, "긴밤자 : ", [x.name for x in long_nighter])

    print("총원 : ", len(p2))
    print("사고자 수 : %d" % (len(accident)), "사고 내용 -> 사고자 : ", [x.name for x in accident], "외출자 : ",
          [x.name for x in outing])
    print("복귀타 없는 외출자 수 : %d" % (len(no_return_work)), "내용 : ", [x.name for x in no_return_work])
    print("현원 : %d, 2타자 수 : %d, 3타자 수 : %d" % (real_worker_size, size_2, size_3))
    print("2타자 : ", [x.name for x in hes_2])
    print("3타자 : ", [x.name for x in hes_3])

    if today_group == 'B':
        for long_night in long_nighter:
            hes_2.remove(long_night)

    return hes_3, hes_2, temp_work, max_work, outing, size_2


# 현재 배치된 사람들이 최대 근무 인원을 얼마나 넘었는지?
def overtime(max_work, temp_work):  # max_work: 오늘 근무 최대 타수, temp_work: 근무 들어간 사람
    check = [0] * len(max_work)  # 각 시간에 초과, 미달한 사람들 수 저장
    for i in range(len(max_work)):
        check[i] = max_work[i] - len(temp_work[i])  # 초과하면 음수 미달 양수
    return check


# 인원 조정 함수
def re_people(check, size_2, today_group):
    check_check = check
    temp = [x for x, t in enumerate(check_check) if t > size_2]
    is_minus = [x for x, t in enumerate(check_check) if t < 0]

    if today_group != 'B':
        if temp != []:  # 2타자는 3타자가 위의 조건대로 들어갔을때만 배치될 수 있다.
            while temp != [] and is_minus != []:  # 재배치 했을때 만족하면 루프 탈출
                x = [a for a, t in enumerate(check_check) if t == min(check_check)]  # 지금 비어 있는 곳에서 제일 적은 자리를 탐색
                t = check_check[temp[0]] - size_2
                check_check[x[len(x) - 1]] += t  # 이왕이면 6시근무 안빼고 4, 8 근무자 중에서 12시 근무로 가는게 낫기 때문
                check_check[temp[0]] -= t
                temp = [x for x, t in enumerate(check_check) if t > size_2]
                is_minus = [x for x, t in enumerate(check_check) if t < 0]
    else:
        if max(check_check) != sum(check_check) - max(check_check):  # 2타자는 3타자가 위의 조건대로 들어갔을때만 배치될 수 있다.
            while max(check_check) != sum(check_check) - max(check_check):  # 재배치 했을때 만족하면 루프 탈출
                x = [a for a, t in enumerate(check_check) if t == min(check_check)]  # 지금 비어 있는 곳에서 제일 적은 자리를 탐색
                t = x[len(x) - 1]  # 이왕이면 6시근무 안빼고 4, 8 근무자 중에서 12시 근무로 가는게 낫기 때문
                check_check[t] += 1
                check_check[check_check.index(max(check_check))] -= 1

    return check_check


# 재배치 함수
def re_arrange(max_work, temp_work, check, today_group, start=0):
    for i in range(len(max_work)):  # 6 4 8 12 근무 시간대 별로 돌린다.
        if check[i] < 0:  # 지금 시간대에 배치된 사람이 만약 최대 근무타수를 초과한다면 음수 이므로 if돌린다
            for __ in range(abs(check[i])):  # 넘은 사람만큼 빼내야 하므로 넘은 사람만큼 루프를 돌린다. 음수를 넣을순 없으니 절댓값
                while True:
                    poor_man = random.choice(temp_work[i])  # 지금 시간대에서 랜덤으로 한명을 뽑는다.
                    if today_group == 'B':
                        wheres_he = [poor_man.wheres_he[start + 0], poor_man.wheres_he[start + 1]]
                        x = [a for a, t in enumerate(wheres_he) if t == 0]
                        y = [b for b, t in enumerate(check) if t > 0]
                    else:
                        x = [a for a, t in enumerate(poor_man.wheres_he) if t == 0]  # 뽑힌 사람이 들어가지 않은 근무 시간 위치를 반환, 저장
                        y = [b for b, t in enumerate(check) if t > 0]  # 현재 자리가 남는 근무 시간 위치를 반환, 저장
                    intersect = list(set(x).intersection(set(y)))  # 뽑힌 사람이 들어가지 않은 근무 시간과, 현재 자리가 남는 근무시간의 교집합을 찾는다
                    if intersect != []:  # 만약 교집합의 자리가 있다면 그 곳으로 뽑힌 사람을 넣는다. 아니면 위 x,y조건에 충족하는 사람을 while 루프로 다시 찾는다.
                        poor_man.wheres_he[intersect[0] + start] = 1
                        poor_man.wheres_he[i + start] = 0
                        temp_work[i].remove(poor_man)
                        temp_work[intersect[0]].append(poor_man)
                        break
                    else:
                        continue
            check = overtime(max_work, temp_work)  # 현재 초과, 미달한 근무 시간을 다시 체크해 준다.

    return temp_work


def re_arrange_2(temp_work, check, today_group, start=0):
    while True:  # 여기서는 타겟 명수로 배치되기 전까지는 함수가 끝나지 않는다.
        for i in range(len(check)):
            if check[i] < 0:
                for __ in range(abs(check[i])):
                    while True:
                        poor_man = random.choice(temp_work[i])
                        if today_group == 'B':
                            wheres_he = [poor_man.wheres_he[start + 0], poor_man.wheres_he[start + 1]]
                            x = [a for a, t in enumerate(wheres_he) if t == 0]
                            y = [b for b, t in enumerate(check) if t > 0]
                        else:
                            x = [a for a, t in enumerate(poor_man.wheres_he) if t == 0]
                            y = [b for b, t in enumerate(check) if t > 0]
                        intersect = list(set(x).intersection(set(y)))
                        if intersect != []:
                            poor_man.wheres_he[intersect[0] + start] = 1
                            poor_man.wheres_he[i + start] = 0
                            temp_work[i].remove(poor_man)
                            temp_work[intersect[0]].append(poor_man)  # 여기까지 re_arrange와 동일
                            check[i] += 1  # 단 여기는 그냥 단순한 연산으로 대체한다.
                            check[intersect[0]] -= 1
                            break
            if today_group == 'B':
                if check[0] == 0 and check[1] == 0:  # 타겟으로 배치가 되었다면 루프 탈출
                    return temp_work
            else:
                if check[0] == 0 and check[1] == 0 and check[2] == 0 and check[3] == 0:  # 타겟으로 배치가 되었다면 루프 탈출
                    return temp_work


def re_assign(max_work, temp_work, check, today_group, size_2):
    if today_group != 'B':
        temp_work = re_arrange(max_work, temp_work, check, today_group)
        # 일단 선호 근무대로 들어간 사람들이 최대 근무 타수를 넘었는지 체크하고 넘었다면 넘지 않도록 재배열
        target = re_people(check, size_2, today_group)  # 근무가 재배열 되었는데 2타자가 들어갈 수 없는 형태라면 ex) 0305 목표 근무 타수를 설정 ex)0404
        check = overtime(max_work, temp_work)  # re_arrange에서 재배열된 사람들이 현재 최대 타수를 넘는지 체크

        if max(check) != sum(check) - max(check):  # 만약 2타자가 들어갈 수 없는 형태로 3타자가 들어갔다면 check가 target이 되도록 3타자 수를 조정
            for i in range(4):
                check[i] = check[i] - target[i]  # check 에서 target을 빼서 어느 시간대가 나와서 어느 시간대로 나와야하는지 체크
            temp_work = re_arrange_2(temp_work, check, today_group)

        check = overtime(max_work, temp_work)  # 현재 얼마나 넘었는지 체크 이는 3타자 배열이 끝나고 2타자 배열 최대 근무 타수에 이용된다.

    else:
        for i in range(2):
            temp_work_t = [temp_work[2 * i], temp_work[2 * i + 1]]
            max_work_t = [max_work[2 * i], max_work[2 * i + 1]]
            check_t = [check[2 * i], check[2 * i + 1]]

            temp_work_t = re_arrange(max_work_t, temp_work_t, check_t, today_group, 2 * i)
            target_t = re_people(check_t, size_2, today_group)
            check_t = overtime(max_work_t, temp_work_t)
            if max(check_t) != sum(check_t) - max(check_t):
                # 만약 2타자가 들어갈 수 없는 형태로 3타자가 들어갔다면 check가 target이 되도록 3타자 수를 조정
                for j in range(2):
                    check_t[j] = check_t[j] - target_t[j]  # check 에서 target을 빼서 어느 시간대가 나와서 어느 시간대로 나와야하는지 체크
                temp_work_t = re_arrange_2(temp_work_t, check_t, today_group, 2 * i)

            check_t = overtime(max_work_t, temp_work_t)  # 현재 얼마나 넘었는지 체크 이는 3타자 배열이 끝나고 2타자 배열 최대 근무 타수에 이용된다.

            check[2 * i], check[2 * i + 1] = check_t[0], check_t[1]
            temp_work[2 * i], temp_work[2 * i + 1] = temp_work_t[0], temp_work_t[1]
            check = overtime(max_work, temp_work)

    return temp_work, check


# 출력 함수
def print_work(today_time, today_group, temp_work):
    print(today_group)
    for i in range(4):
        print(today_time[i], "\t", [x.name for x in temp_work[i]])


# 근무 계산
def scheduler():
    today_time = Timetable[which_group][0]  # 오늘 근무 시간
    today_group = work_group[which_group]  # 오늘 근무 조
    max_work = Timetable[which_group][is_weekend]  # 오늘 근무 최대 타수
    real_worker, outing, accident = whos_out(p2)  # 실 근무자, 사고자, 외출자 계산
    true_real_worker = real_worker
    temp_work = [[], [], [], []]  # 세타 근무 들어간 사람
    temp_work_2 = [[], [], [], []]  # 두타 근무 들어간 사람
    hes_3, hes_2, temp_work, max_work, outing, size_2 = whos_3_2(real_worker, outing, today_group, accident, temp_work,
                                                                 max_work)
    # 3타자, 2타자
    for worker in hes_3:  # 3타자 우선
        for i in range(3):
            temp_work[today_time.index(worker.times3[today_group][i])].append(worker)
            # temp_work에 3타자의 선호 근무대로 객체 입력
            worker.wheres_he[today_time.index(worker.times3[today_group][i])] = 1  # 객체 내부 변수에 현재 객체의 들어간 근무 입력

    check = overtime(max_work, temp_work)  # 들어간 사람들 중에서 최대 근무 타수 중에서 얼마나 초과, 미달했는지 리스트
    temp_work, max_work_2 = re_assign(max_work, temp_work, check, today_group, size_2)
    # 2타자로 넘기기 전에 2타자가 들어갈 수 있도록 3타자 위치 조정,max_work_2는 조정에 따른 2타자가 들어갈 수 있는 위치, 최대 타수

    for worker in hes_2:
        for i in range(2):
            temp_work_2[today_time.index(worker.times2[today_group][i])].append(worker)
            worker.wheres_he[today_time.index(worker.times2[today_group][i])] = 1

    check_2 = overtime(max_work_2, temp_work_2)  # 3타자와 동일
    temp_work_2, xxx = re_assign(max_work_2, temp_work_2, check_2, today_group,
                                 size_2)  # 3타자와 동일, xxx는 딱히 필요없는 변수라 xxx라고 함

    if today_group != 'B':
        temp_work[3] += outing

    for i in range(4):
        temp_work[i] += temp_work_2[i]
    print_work(today_time, today_group, temp_work)

    return temp_work, true_real_worker, outing


scheduled_work, real_worker, outing = scheduler()
real_worker= real_worker+outing
'''
def lets_make_rank(args):  # 리스트 셔플하기
    h_list = []
    for h in args:
        h_list.append(h)
    random.shuffle(h_list)
    return h_list


def random_index_except_zero(list):
    a = random.randint(0, len(list) - 1)
    while True:
        if list[a] > 0:
            break
        else:
            a = random.randint(0, len(list) - 1)
    return a


def make_column_list(mat, n):
    list = []
    for i in range(len(mat)):
        list.append(mat[i][n])

    return list


def reset(workers):
    for h in workers:
        h.work = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]


def jung_rearrange(workers, temp_jung ,max_place ,start=0):
    for h in workers:  # 랜덤 시간대를 골라 정출 한개 픽스

        a = random_index_except_zero(h.wheres_he)
        h.work[0][a] = 1
        h.wheres_he[a] = 0  # 정출 들어간 시간대는 0으로 바꿈
        max_place[a][0] -= 1
        temp_jung[a].append(h)
    check = []
    for i in range(4):
        check.append(max_place[i][0])
    print(check)
    for i in range(4):  # 6 4 8 12 근무 시간대 별로 돌린다.
        if check[i] < 0:  # 지금 시간대에 배치된 사람이 만약 최대 정출 타수를 초과한다면 음수 이므로 if돌린다
            for j in range(abs(check[i])):  # 넘은 사람만큼 빼내야 하므로 넘은 사람만큼 루프를 돌린다. 음수를 넣을순 없으니 절댓값
                while True:
                    poor_man = random.choice(temp_jung[i])  # 지금 시간대에서 랜덤으로 한명을 뽑는다.
                    x = [a for a, t in enumerate(poor_man.wheres_he) if t == 1]  # 해당 시간 외에 다른 근무 시간 위치 반환
                    y = [b for b, t in enumerate(check) if t > 0]  # 현재 자리가 남는 근무 시간 위치를 반환, 저장
                    intersect = list(set(x).intersection(set(y)))  # 뽑힌 사람이 들어가지 않은 근무 시간과, 현재 자리가 남는 근무시간의 교집합을 찾는다
                    if intersect != []:  # 만약 교집합의 자리가 있다면 그 곳으로 뽑힌 사람을 넣는다. 아니면 위 x,y조건에 충족하는 사람을 while 루프로 다시 찾는다.
                        poor_man.wheres_he[intersect[0]+start] = 0
                        poor_man.wheres_he[i+start] = 1
                        temp_jung[i].remove(poor_man)
                        max_place[i][0]+=1
                        max_place[intersect[0]+start][0]-=1
                        temp_jung[intersect[0]].append(poor_man)
                        check[i]+=1
                        check[intersect[0]]-=1
                        break
                    else:
                        continue
    check = []
    for i in range(4):
        check.append(max_place[i][0])

    print(check)



def schedule_place(workers):

    count = 0
    workers=lets_make_rank(workers)


    #max_place = [[5, 3, 2, 1], [5, 3, 2, 1], [5, 3, 2, 1], [2, 2, 1, 1]]

    #max_place = [[5, 3, 2, 1], [5, 3, 2, 1], [2, 2, 1, 1], [2, 2, 1, 1]]

    max_place = placetable[which_group][is_weekend - 1]
    deter = 0
    temp_jung=[[],[],[],[]] #정출에 들어가는 사람 리스트

    if int(sum([max_place[i][0] for i in range(4)])) >= len(workers):# 현 근무자수보다 정출 타수가 많거나 같을 경우
        poors = abs(int(sum([max_place[i][0] for i in range(4)])) - len(workers))
        for __ in range(poors):
            for i in range(len(workers)):
                if sum(workers[i].wheres_he) == 3:  # 3타자 중에서 정출을 두번 줌
                    place_number = [1, 2, 3]
                    unlucky = workers[i].wheres_he[:]
                    a = random.choice(place_number)
                    max_place[unlucky.index(1)][0] -= 1
                    workers[i].work[0][unlucky.index(1)] = 1
                    unlucky.remove(1)

                    max_place[unlucky.index(1) + 1][a] -= 1
                    workers[i].work[a][unlucky.index(1) + 1] =1
                    unlucky.remove(1)
                    max_place[unlucky.index(1) + 2][0] -= 1
                    workers[i].work[0][unlucky.index(1) + 2] = 1
                    #print(workers[i].work, end="\n")
                    print(workers[i].name, end=' ')
                    whatis_hwork(workers[i].work)
                    workers.remove(workers[i])
                    break

        jung_rearrange(workers, temp_jung, max_place)

    elif int(sum([max_place[i][0] for i in range(4)])) < len(workers): #현 근무자가 타수보다 많을 경우
        no_jung= abs(int(sum([max_place[i][0] for i in range(4)])) - len(workers))
        temp_workers=workers[0:len(workers)-no_jung]


        jung_rearrange(temp_workers, temp_jung, max_place)

    # 정출 제외한 근무지 무한 루프
    real_workers=copy.deepcopy(workers)
    r_max_place=copy.deepcopy(max_place)
    while True:
        for h in real_workers:
            n = 0
            for t in h.wheres_he:
                if t == 1:
                    a = random_index_except_zero(r_max_place[n])
                    r_max_place[n][a] = r_max_place[n][a] - 1
                    h.work[a][n] = h.work[a][n] + 1
                    n += 1
                else:
                    n += 1
            for list in h.work:
                if sum(list) >= 2:
                    deter += 1

        if deter == 0:
            print(count)
            break

        else:
            real_workers=copy.deepcopy(workers)
            r_max_place = copy.deepcopy(max_place)
            count+=1 #w
            deter=0
            print(count)

    return real_workers

def whatis_hwork(mat):
    if 1 in mat[0]:
        if 1 == mat[0][0]:
            print(Timetable[which_group][0][0],"-정출",end=' ')
        if 1 == mat[0][1]:
            print(Timetable[which_group][0][1],"-정출",end=' ')
        if 1 == mat[0][2]:
            print(Timetable[which_group][0][2],"-정출",end=' ')
        if 1 == mat[0][3]:
            print(Timetable[which_group][0][3],"-정출",end=' ')
    if 1 in mat[1]:
        if 1 == mat[1][0]:
            print(Timetable[which_group][0][0],"-별정",end=' ')
        if 1 == mat[1][1]:
            print(Timetable[which_group][0][1],"-별정",end=' ')
        if 1 == mat[1][2]:
            print(Timetable[which_group][0][2],"-별정",end=' ')
        if 1 == mat[1][3]:
            print(Timetable[which_group][0][3],"-별정",end=' ')
    if 1 in mat[2]:
        if 1 == mat[2][0]:
            print(Timetable[which_group][0][0], "-별후",end=' ')
        if 1 == mat[2][1]:
            print(Timetable[which_group][0][1], "-별후",end=' ')
        if 1 == mat[2][2]:
            print(Timetable[which_group][0][2], "-별후",end=' ')
        if 1 == mat[2][3]:
            print(Timetable[which_group][0][3], "-별후",end=' ')
    if 1 in mat[3]:
        if 1 == mat[3][0]:
            print(Timetable[which_group][0][0], "-서남문",end=' ')
        if 1 == mat[3][1]:
            print(Timetable[which_group][0][1], "-서남문",end=' ')
        if 1 == mat[3][2]:
            print(Timetable[which_group][0][2], "-서남문",end=' ')
        if 1 == mat[3][3]:
            print(Timetable[which_group][0][3], "-서남문",end=' ')
    print()

result=schedule_place(real_worker)

for h in result:
    print(h.name,end=' ')
    whatis_hwork(h.work)

'''