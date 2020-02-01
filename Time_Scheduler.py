import random
import copy

# 외출자, 사고자 입력, 실 근무자 계산
def whos_out(p2, today_group, max_work):
    acci = ['Member01', 'Member08', 'Member02', 'Member21']  # input("사고자 입력 : ").split()
    out = ['Member17', 'Member10', 'Member06', 'Member14']  # ("외출자 입력 : ").split()
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
def whos_3_2(real_worker, outing, today_group, temp_work, max_work, is_weekend, no_return_work, raw_outing):
    real_worker_size = len(real_worker)  # 현원(총원 - 외출자 - 사고자)
    size_2 = real_worker_size * 3 - sum(max_work) + len(raw_outing)  # 2타자 수
    size_3 = real_worker_size - size_2  # 3타자 수
    hes_3, hes_2, hes_1, long_nighter = [], [], [], []  # 3타자, 2타자, 긴밤자
    size_1 = 0

    if is_weekend == 2:  # 주말에는 size_2가 2타자 + 복귀타 없는 외출자로 계산되서 빼줌
        size_2 -= len(no_return_work)
        size_3 = real_worker_size - size_2

    if today_group == 'B':  # 외출자들 수 만큼 미리 최대 근무 타수 조정
        if max_work[3] - len(outing) < 0:  # B조에서 복귀타 수가 막타자(4시근무) 수 초과 시
            max_work[2] -= len(outing) - max_work[3]
            max_work[3] -= max_work[3]
        else:
            max_work[3] -= len(outing)
    else:  # a,c조에서는 이미 잘려서 괜찮다
        max_work[3] -= len(outing)

    if size_3 >= 0:
        if size_2 > 0 and is_weekend == 1:  # 2타자 자동 계산
            start_2 = 'Member12'  # input("2타 시작 입력 : ")
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
            long_night_size = real_worker_size - max_work[2] - max_work[3]  # 긴밤자 수
            if long_night_size > 0:
                temp_work, long_nighter = whos_long_night(hes_2, temp_work, long_night_size)
            for long_night in long_nighter:
                hes_2.remove(long_night)
        else:
            long_nighter = []
    else:  # 1타
        size_2 = real_worker_size + size_3
        size_1 = real_worker_size - size_2

        if is_weekend == 2:  # 주말 한타는 그냥 올 두타로 만들어버린다
            max_work[3] += size_1
            for __ in range(size_1):
                a = random.choice(outing)
                outing.remove(a)
                no_return_work.append(a)
            size_2 += size_1
            size_1 = size_3 = 0
            hes_2 = copy.deepcopy(real_worker)

        if size_1 > 0 and is_weekend == 1:  # 1타자 자동 계산
            start_1 = 'Member12'  # input("1타 시작 입력 : ")
            for member in real_worker:
                if member.name == start_1:
                    index = real_worker.index(member)
                    for i in range(size_1):
                        hes_1.append(real_worker[(i + index) % real_worker_size])
                    break
            for member in real_worker:
                if member not in hes_1:
                    hes_2.append(member)

        if today_group == 'B':
            long_night_size = real_worker_size - max_work[2] - max_work[3]  # 긴밤자 수
            if long_night_size > 0:
                temp_work, long_nighter = whos_long_night(hes_2, temp_work, long_night_size)
            for long_night in long_nighter:
                hes_2.remove(long_night)
        else:
            long_nighter = []

    return hes_3, hes_2, hes_1, temp_work, max_work, outing, size_2, size_1, long_nighter


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
def re_arrange(max_work, temp_work_t, check_t, today_group, start=0):
    count = 0
    # temp_work = copy.deepcopy(temp_work_t)
    # check = copy.deepcopy(check_t)
    temp_work = temp_work_t
    check = check_t

    for i in range(len(max_work)):  # 6 4 8 12 근무 시간대 별로 돌린다.
        if check[i] < 0:  # 지금 시간대에 배치된 사람이 만약 최대 근무타수를 초과한다면 음수 이므로 if돌린다
            t = check[i]
            for __ in range(abs(t)):  # 넘은 사람만큼 빼내야 하므로 넘은 사람만큼 루프를 돌린다. 음수를 넣을순 없으니 절댓값
                while True:
                    check = overtime(max_work, temp_work)  # 현재 초과, 미달한 근무 시간을 다시 체크해 준다.
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
                        count = 0
                        break
                    count += 1
                    if int(count / 50) >= 1:
                        which_one = random.choice(x)
                        tt = random.choice(temp_work[which_one])
                        if tt.wheres_he[y[0]] == 0:
                            tt.wheres_he[which_one] = 0
                            tt.wheres_he[y[0]] = 1
                            temp_work[which_one].remove(tt)
                            temp_work[y[0]].append(tt)
                            poor_man.wheres_he[y[0]] = 0
                            poor_man.wheres_he[which_one] = 1
                            temp_work[which_one].append(poor_man)
                            temp_work[y[0]].remove(poor_man)

                    if count > 200:
                        return -1

    return temp_work


def re_arrange_2(temp_work_t, check_t, today_group, start=0):
    # temp_work = copy.deepcopy(temp_work_t)
    # check = copy.deepcopy(check_t)

    temp_work = temp_work_t
    check = check_t

    while True:  # 여기서는 타겟 명수로 배치되기 전까지는 함수가 끝나지 않는다.
        for i in range(len(check)):
            if check[i] < 0:
                t = check[i]
                for __ in range(abs(t)):
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


def re_assign(max_work, temp_work_tt, check_tt, today_group, size_2=-1):
    if size_2 != -1:
        if today_group != 'B':
            while True:
                # check = copy.deepcopy(check_tt)
                # temp_work = copy.deepcopy(temp_work_tt)
                check = check_tt
                temp_work = temp_work_tt
                temp_work = re_arrange(max_work, temp_work, check, today_group)
                if temp_work != -1:
                    break

            # 일단 선호 근무대로 들어간 사람들이 최대 근무 타수를 넘었는지 체크하고 넘었다면 넘지 않도록 재배열
            check = overtime(max_work, temp_work)  # re_arrange에서 재배열된 사람들이 현재 최대 타수를 넘는지 체크
            target = re_people(check, size_2, today_group)  # 근무가 재배열 되었는데 2타자가 들어갈 수 없는 형태라면 ex) 0305 목표 근무 타수를 설정 ex)0404

            for i in range(4):
                check[i] = check[i] - target[i]  # check 에서 target을 빼서 어느 시간대가 나와서 어느 시간대로 나와야하는지 체크
            temp_work = re_arrange_2(temp_work, check, today_group)
            check = overtime(max_work, temp_work)  # 현재 얼마나 넘었는지 체크 이는 3타자 배열이 끝나고 2타자 배열 최대 근무 타수에 이용된다.

        else:
            for i in range(2):
                while True:
                    temp_work_t = copy.deepcopy([temp_work_tt[2 * i], temp_work_tt[2 * i + 1]])
                    max_work_t = copy.deepcopy([max_work[2 * i], max_work[2 * i + 1]])
                    check_t = copy.deepcopy([check_tt[2 * i], check_tt[2 * i + 1]])

                    temp_work_t = re_arrange(max_work_t, temp_work_t, check_t, today_group, 2 * i)
                    if temp_work_t != -1:
                        break

                check_t = overtime(max_work_t, temp_work_t)
                target_t = re_people(check_t, size_2, today_group)
                # if max(check_t) != sum(check_t) - max(check_t):
                # 만약 2타자가 들어갈 수 없는 형태로 3타자가 들어갔다면 check가 target이 되도록 3타자 수를 조정
                for j in range(2):
                    check_t[j] = check_t[j] - target_t[j]  # check 에서 target을 빼서 어느 시간대가 나와서 어느 시간대로 나와야하는지 체크

                temp_work_t = re_arrange_2(temp_work_t, check_t, today_group, 2 * i)
                check_t = overtime(max_work_t, temp_work_t)  # 현재 얼마나 넘었는지 체크 이는 3타자 배열이 끝나고 2타자 배열 최대 근무 타수에 이용된다.

                check_tt[2 * i], check_tt[2 * i + 1] = check_t[0], check_t[1]
                temp_work_tt[2 * i], temp_work_tt[2 * i + 1] = temp_work_t[0], temp_work_t[1]
                check = overtime(max_work, temp_work_tt)
            check = check_tt
            temp_work = temp_work_tt
    else:
        if today_group != 'B':
            while True:
                check = copy.deepcopy(check_tt)
                temp_work = copy.deepcopy(temp_work_tt)
                temp_work = re_arrange(max_work, temp_work, check, today_group)
                if temp_work != -1:
                    break

            check = overtime(max_work, temp_work)  # 현재 얼마나 넘었는지 체크 이는 3타자 배열이 끝나고 2타자 배열 최대 근무 타수에 이용된다.

        else:
            for i in range(2):
                while True:
                    temp_work_t = copy.deepcopy([temp_work_tt[2 * i], temp_work_tt[2 * i + 1]])
                    max_work_t = copy.deepcopy([max_work[2 * i], max_work[2 * i + 1]])
                    check_t = copy.deepcopy([check_tt[2 * i], check_tt[2 * i + 1]])

                    temp_work_t = re_arrange(max_work_t, temp_work_t, check_t, today_group, 2 * i)
                    if temp_work_t != -1:
                        break

                check_t = overtime(max_work_t, temp_work_t)  # 현재 얼마나 넘었는지 체크 이는 3타자 배열이 끝나고 2타자 배열 최대 근무 타수에 이용된다.

                check_tt[2 * i], check_tt[2 * i + 1] = check_t[0], check_t[1]
                temp_work_tt[2 * i], temp_work_tt[2 * i + 1] = temp_work_t[0], temp_work_t[1]
                check = overtime(max_work, temp_work_tt)
            check = check_tt
            temp_work = temp_work_tt
    return temp_work, check


def lets_make_rank(args):  # 리스트 셔플하기
    h_list = []
    for h in args:
        h_list.append(h)
    random.shuffle(h_list)
    return h_list


# 비상 출력
def printing(tt):
    for i in range(4):
        print("\t", [x.name for x in tt[i]])
    print('temp_work들어간 사람')
    c = []
    for a in tt:
        for b in a:
            if b not in c:
                c.append(b)
                print(b.name, b.wheres_he)
    print(len(c))


# 출력 함수
def print_work(today_time, today_group, temp_work, p2, accident, outing, no_return_work, real_worker, hes_1, hes_2, hes_3, long_nighter=[]):
    print(today_group)
    print("총원 : ", len(p2))
    print("사고자 수 : %d" % (len(accident)), "\n외출자 수 %d" % (len(outing)), "\n\n사고 내용\n사고자 : ", [x.name for x in accident], "\n외출자 : ", [x.name for x in outing])
    print("\n복귀타 없는 외출자 수 : %d" % (len(no_return_work)), "\n내용 : ", [x.name for x in no_return_work])
    print("\n현원 : %d" % len(real_worker))
    print("1타자 수 : %d" % len(hes_1), [x.name for x in hes_1])
    print("2타자 수 : %d" % len(hes_2), [x.name for x in hes_2])
    print("3타자 수 : %d" % len(hes_3), [x.name for x in hes_3])
    if today_group == 'B':
        print("긴밤자 수 : %d" % len(long_nighter), "긴밤자 : ", [x.name for x in long_nighter])
    for i in range(4):
        print(today_time[i], "\t", [x.name for x in temp_work[i]])


# 근무 계산
def scheduler(Timetable, which_group, work_group, is_weekend, p2):
    today_time = Timetable[which_group][0]  # 오늘 근무 시간
    today_group = work_group[which_group]  # 오늘 근무 조
    max_work = copy.deepcopy(Timetable[which_group][is_weekend])  # 오늘 근무 최대 타수
    real_max_work = copy.deepcopy(Timetable[which_group][is_weekend])
    temp_work = [[], [], [], []]  # 세타 근무 들어간 사람
    temp_work_2 = [[], [], [], []]  # 두타 근무 들어간 사람\

    real_worker, outing, accident, no_return_work, raw_outing = whos_out(p2, today_group, max_work)  # 실 근무자, 사고자, 외출자 계산
    hes_3, hes_2, hes_1, temp_work, max_work, outing, size_2, size_1, long_nighter = whos_3_2(real_worker, outing, today_group, temp_work, max_work, is_weekend, no_return_work, raw_outing)

    if hes_1 == []:  # 3타자, 2타자
        if len(hes_3) != 0:
            for worker in hes_3:  # 3타자 우선
                for i in range(3):
                    temp_work[today_time.index(worker.times3[today_group][i])].append(worker)  # temp_work에 3타자의 선호 근무대로 객체 입력
                    worker.wheres_he[today_time.index(worker.times3[today_group][i])] = 1  # 객체 내부 변수에 현재 객체의 들어간 근무 입력

            check = overtime(max_work, temp_work)  # 들어간 사람들 중에서 최대 근무 타수 중에서 얼마나 초과, 미달했는지 리스트
            temp_work, max_work_2 = re_assign(max_work, temp_work, check, today_group, size_2)
            # 2타자로 넘기기 전에 2타자가 들어갈 수 있도록 3타자 위치 조정,max_work_2는 조정에 따른 2타자가 들어갈 수 있는 위치, 최대 타수
        else:  # 올두타
            max_work_2 = copy.deepcopy(max_work)
            temp_work_2 = copy.deepcopy(temp_work)

        for worker in hes_2:
            for i in range(2):
                temp_work_2[today_time.index(worker.times2[today_group][i])].append(worker)
                worker.wheres_he[today_time.index(worker.times2[today_group][i])] = 1

        check_2 = overtime(max_work_2, temp_work_2)  # 3타자와 동일
        temp_work_2, xxx = re_assign(max_work_2, temp_work_2, check_2, today_group, size_2)  # 3타자와 동일, xxx는 딱히 필요없는 변수라 xxx라고 함

        if today_group != 'B':
            temp_work[3] += outing
        else:
            if real_max_work[2] - max_work[2] > 0:
                out_last_worker = random.sample(outing, real_max_work[2] - max_work[2])
                temp_work[2] += out_last_worker
                for tt in outing:
                    if tt not in out_last_worker:
                        temp_work[3] += [tt]
            else:
                temp_work[3] += outing

        for i in range(4):
            temp_work[i] += temp_work_2[i]

    else:
        for worker in hes_2:  # 2타자 우선
            for i in range(2):
                temp_work[today_time.index(worker.times2[today_group][i])].append(worker)  # temp_work에 3타자의 선호 근무대로 객체 입력
                worker.wheres_he[today_time.index(worker.times2[today_group][i])] = 1  # 객체 내부 변수에 현재 객체의 들어간 근무 입력

        check = overtime(max_work, temp_work)  # 들어간 사람들 중에서 최대 근무 타수 중에서 얼마나 초과, 미달했는지 리스트
        temp_work, max_work_2 = re_assign(max_work, temp_work, check, today_group)
        # max_work_2는 조정에 따른 1타자가 들어갈 수 있는 위치, 최대 타수

        hes_1 = lets_make_rank(hes_1)

        for member in hes_1:
            for i in range(len(max_work_2)):
                if max_work_2[i] > 0:
                    temp_work[i].append(member)
                    max_work_2[i] -= 1
                    member.wheres_he[i] = 1

        if today_group != 'B':
            temp_work[3] += outing
        else:
            if real_max_work[3] - len(outing) < 0:  # B조에서 복귀타 수가 막타자(4시근무) 수 초과 시
                out_last_worker = random.sample(outing, real_max_work[3])
                temp_work[3] += out_last_worker
                for tt in outing:
                    if tt not in out_last_worker:
                        temp_work[2] += [tt]
            else:
                temp_work[3] += outing

        for i in range(4):
            temp_work[i] += temp_work_2[i]
    print_work(today_time, today_group, temp_work, p2, accident, outing, no_return_work, real_worker, hes_1, hes_2, hes_3, long_nighter)

    return temp_work, real_worker, outing
