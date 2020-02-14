import constants
import random
import copy
import pprint

Timetable = copy.deepcopy(constants.Timetable)
work_group = copy.deepcopy(constants.work_group)
which_group = copy.deepcopy(constants.which_group)
is_weekend = copy.deepcopy(constants.is_weekend)


def lets_make_rank(args):  # 리스트 셔플하기
    h_list = []
    for h in args:
        h_list.append(h)
    random.shuffle(h_list)
    return h_list


def random_index_except_zero(list):
    a = random.randint(0, len(list) - 1)
    while True:
        if sum(list) == 0:
            return -1
        elif list[a] > 0:
            break
        else:
            a = random.randint(0, len(list) - 1)
    return a



def make_column_list(mat, n):
    list = []
    for i in range(len(mat)):
        list.append(mat[i][n])

    return list


def jung_2times(workers, poor_man, max_place, jung_2):  # 3타자 중 첫번째, 3번째 근무에 정출 2번 투입
    place_number = [1, 2, 3]
    unlucky = poor_man.wheres_he[:]
    max_place[unlucky.index(1)][0] -= 1  # unluck.index(1)은 첫번째 근무 시간
    poor_man.work[0][unlucky.index(1)] = 1
    unlucky.remove(1)
    a = random.choice(place_number)
    max_place[unlucky.index(1) + 1][a] -= 1
    poor_man.work[a][unlucky.index(1) + 1] = 1  # 정출을 제외한 근무지 2번째 시간에 투입
    unlucky.remove(1)
    max_place[unlucky.index(1) + 2][0] -= 1
    poor_man.work[0][unlucky.index(1) + 2] = 1
    jung_2.append(poor_man)
    # print(poor_man.name, end=' ')
    # whatis_hwork(poor_man.work)
    workers.remove(poor_man)  # 정출 2번 들어간 worker는 이후 있을 근무지 배정에서


def jung_rearrange(workers, temp_jung, max_place):
    count = 0

    for h in workers:  # 랜덤 시간대를 골라 정출 한개 픽스

        a = random_index_except_zero(h.wheres_he)
        h.work[0][a] = 1
        h.wheres_he[a] = 0  # 정출 들어간 시간대는 0으로 바꿈
        max_place[a][0] -= 1
        temp_jung[a].append(h)
    check = []
    for i in range(4):
        check.append(max_place[i][0])
    # print(check)
    for i in range(4):  # 6 4 8 12 근무 시간대 별로 돌린다.
        if check[3 - i] < 0:  # 지금 시간대에 배치된 사람이 만약 최대 정출 타수를 초과한다면 음수 이므로 if돌린다
            for j in range(abs(check[3 - i])):  # 넘은 사람만큼 빼내야 하므로 넘은 사람만큼 루프를 돌린다. 음수를 넣을순 없으니 절댓값
                while True:
                    if temp_jung[3 - i] == []:
                        count += 1
                        if count > 50:
                            break
                        continue
                    poor_man = random.choice(temp_jung[3 - i])  # 지금 시간대에서 랜덤으로 한명을 뽑는다
                    x = [a for a, t in enumerate(poor_man.wheres_he) if t == 1]  # 해당 시간 외에 다른 근무 시간 위치 반환
                    y = [b for b, t in enumerate(check) if t > 0]  # 현재 자리가 남는 근무 시간 위치를 반환, 저장
                    intersect = list(set(x).intersection(set(y)))  # 뽑힌 사람이 들어가지 않은 근무 시간과, 현재 자리가 남는 근무시간의 교집합을 찾는다
                    if intersect != []:  # 만약 교집합의 자리가 있다면 그 곳으로 뽑힌 사람을 넣는다. 아니면 위 x,y조건에 충족하는 사람을 while 루프로 다시 찾는다.
                        poor_man.wheres_he[intersect[0]] = 0
                        poor_man.wheres_he[3 - i] = 1
                        temp_jung[3 - i].remove(poor_man)
                        temp_jung[intersect[0]].append(poor_man)
                        max_place[3 - i][0] += 1
                        max_place[intersect[0]][0] -= 1
                        poor_man.work[0][3 - i] = 0
                        poor_man.work[0][intersect[0]] = 1
                        check[3 - i] += 1
                        check[intersect[0]] -= 1
                        break
                    else:
                        count += 1
                        if count > 50:
                            break

    if count < 50:
        return 0

    else:
        return -1


def schedule_place(f_workers, f_outing):
    tt = []
    jung_2 = []  #정출 두번뛰는 worker들 리스트
    for h in f_workers:  # 한 타자들은 외출자로 간주하여 worker에서 제외시키고 outing에 대입
        if sum(h.wheres_he) == 1:
            f_outing.append(h)
            tt.append(h)
    for h in tt:
        if h in f_workers:
            f_workers.remove(h)

    sec_count = 0  # 두번째 while문 돌릴 때 쓰는 count
    first_count = 0  #첫번째 while문 돌릴 때 쓰는 count

    escape = True
    len_outing = len(f_outing[:])  # 변하지 않는 한타자와 외출자의 수
    placetable = copy.deepcopy(constants.placetable)
    max_place = placetable[which_group][is_weekend - 1]
    deter = 0

    # 정출에 들어가는 사람 리스트

    while True:
        outing = copy.deepcopy(f_outing)
        # outing = lets_make_rank(outing)  outing배열의 마지막 쪽에 한타자들을 위치하게끔 유도, 셔플돌리지 않는다. ? 왜 이렇게 해놨지??
        outing = lets_make_rank(outing)
        workers = copy.deepcopy(f_workers)
        workers = lets_make_rank(workers)
        temp_jung = [[], [], [], []]
        if len(outing) <= 2:  # 앞으로 있을 정출 근무자 수 계산을 위해 한타자들 중 2명을 정출 배열에 투입

            workers = workers + outing

            outing = []

        elif len_outing == 11:
            workers = workers + outing[0:3]
            outing = outing[3:]  # outing은 정출 배열에 제외되고 나머지 근무지에 투입될 예정

        elif len_outing == 12:
            workers = workers + outing[0:4]
            outing = outing[4:]  # outing은 정출 배열에 제외되고 나머지 근무지에 투입될 예정

        else:
            workers = workers + outing[0:2]
            outing = outing[2:]  # outing은 정출 배열에 제외되고 나머지 근무지에 투입될 예정

        if int(sum([max_place[i][0] for i in range(4)])) >= len(workers):  # 현 근무자수보다 정출 타수가 많거나 같을 경우
            poors = abs(int(sum([max_place[i][0] for i in range(4)])) - len(workers))  # 정출 두번들어가는 사람의 수
            if work_group[which_group] == 'B':
                for __ in range(poors):
                    for i in range(len(workers)):
                        if sum(workers[i].wheres_he) == 3 and workers[i].wheres_he[2] == 1:  # 3타자 중, 새벽 2시에 근무 있는 사람을 두번줌, 4시는 outing이 채울 예정
                            jung_2times(workers, workers[i], max_place, jung_2)
                            break
            else:
                if len_outing >= 2:
                    for __ in range(poors):
                        for i in range(len(workers)):
                            if sum(workers[i].wheres_he) == 3 and workers[i].wheres_he[3] == 0:  # 3타자 중에서 정출을 두번 줌
                                jung_2times(workers, workers[i], max_place, jung_2)
                                break

                else:  # 에라 모르겠다.
                    for __ in range(poors):
                        for i in range(len(workers)):
                            if sum(workers[i].wheres_he) == 3:  # 3타자 중, 막타 있는 사람만 줌
                                jung_2times(workers, workers[i], max_place, jung_2)
                                break

            r_workers = copy.deepcopy(workers)
            real_max_place = copy.deepcopy(max_place)
            result = jung_rearrange(r_workers, temp_jung, real_max_place)
            if result == 0:
                workers = r_workers
                max_place = real_max_place
                break
            else:
                first_count += 1
                if first_count > 100:
                    escape = False
                    break
                continue


        elif int(sum([max_place[i][0] for i in range(4)])) < len(workers):  # 현 근무자가 타수보다 많을 경우
            no_jung = abs(int(sum([max_place[i][0] for i in range(4)])) - len(workers))
            temp_workers = workers[no_jung:]  # 외출자들은 무조건 정출에 포함되게끔 만든 트릭

            r_workers = copy.deepcopy(temp_workers)
            real_max_place = copy.deepcopy(max_place)
            result = jung_rearrange(r_workers, temp_jung, real_max_place)
            if result == 0:
                workers[no_jung:] = r_workers
                max_place = real_max_place
                break
            else:
                first_count += 1
                if first_count > 100:
                    escape = False

                    break
                continue


    # 정출 제외한 근무지 무한 루프
    workers = workers + outing
    try:
        while True:
            real_workers = copy.deepcopy(workers)
            r_max_place = copy.deepcopy(max_place)
            for h in real_workers:
                n = 0
                for t in h.wheres_he:
                    if t == 1:
                        a = random_index_except_zero(r_max_place[n])
                        if a == -1:
                            print("근무 짜기가 실패하였습니다. 다시 돌려주세요 ㅎㅎ")
                            return -1
                        r_max_place[n][a] = r_max_place[n][a] - 1
                        h.work[a][n] = h.work[a][n] + 1
                        n += 1
                    else:
                        n += 1
                for list in h.work:
                    if sum(list) >= 2:
                        deter += 1

            if deter == 0:
                # print(sec_count)
                break

            else:

                sec_count += 1
                deter = 0
                if sec_count == 2000:
                    escape = False  # count가 적당히 커지면 어차피 안되는 거니까 함수 처음부터 다시 돌리기
                    break
    except:
        escape = False
    if escape == False:
        print("근무 짜기가 실패하였습니다. 다시 돌려주세요 ㅎㅎ")
        return -1
    for poor_man in jung_2:
        print(poor_man.name, end=' ')
        whatis_hwork(poor_man.work)

    return real_workers


def whatis_hwork(mat):
    t = [''] * 4
    strr = ['정출', '별정', '별후', '서남문']
    for i in range(4):
        for j in range(4):
            if mat[j][i] == 1:
                t[i] = strr[j]
                print("%d%4s" % (Timetable[which_group][0][i], strr[j]), end=' ')
                break
    print()
