import constants
import random
import copy

Timetable = copy.deepcopy(constants.Timetable)
placetable = copy.deepcopy(constants.placetable)
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


def jung_2times(workers, poor_man, max_place):
    place_number = [1, 2, 3]
    unlucky = poor_man.wheres_he[:]
    max_place[unlucky.index(1)][0] -= 1  # unluck.index(1)은 첫번째 근무 시간
    poor_man.work[0][unlucky.index(1)] = 1
    unlucky.remove(1)
    a = random.choice(place_number)
    max_place[unlucky.index(1) + 1][a] -= 1
    poor_man.work[a][unlucky.index(1) + 1] = 1
    unlucky.remove(1)
    max_place[unlucky.index(1) + 2][0] -= 1
    poor_man.work[0][unlucky.index(1) + 2] = 1
    # print(workers[i].work, end="\n")
    print(poor_man.name, end=' ')
    whatis_hwork(poor_man.work)
    workers.remove(poor_man)


def jung_rearrange(workers, temp_jung, max_place):
  
    count=0
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
        if check[3-i] < 0:  # 지금 시간대에 배치된 사람이 만약 최대 정출 타수를 초과한다면 음수 이므로 if돌린다
            for j in range(abs(check[3-i])):  # 넘은 사람만큼 빼내야 하므로 넘은 사람만큼 루프를 돌린다. 음수를 넣을순 없으니 절댓값
                while True:
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
                    
                    count+=1
                    if count>30:
                      return -1
                        
                        
    check = []
    for i in range(4):
        check.append(max_place[i][0])

    print(check)
    return 0

def schedule_place(workers, outing):
    while True:
        count = 0
        workers = lets_make_rank(workers)
        outing = lets_make_rank(outing)
        len_outing = len(outing[:])
        max_place = placetable[which_group][is_weekend - 1]
        deter = 0
        escape = True
        temp_jung = [[], [], [], []]  # 정출에 들어가는 사람 리스트
        '''if work_group[which_group] == 'B':  # 외출자 수 계산 후 정출 들어갈 외출자 pick
            if len(outing) <= 4:
                workers = workers + outing
                outing = []

            else:
                workers = workers + outing[0:4]
                outing = outing[4:]'''
        
        if len(outing) <= 2:
            workers = workers + outing
            outing = []

        else:
            workers = workers + outing[0:2]
            outing = outing[2:]

        if int(sum([max_place[i][0] for i in range(4)])) >= len(workers):  # 현 근무자수보다 정출 타수가 많거나 같을 경우
            poors = abs(int(sum([max_place[i][0] for i in range(4)])) - len(workers))
            if work_group[which_group] == 'B': 
              for __ in range(poors):
                    for i in range(len(workers)):
                        if sum(workers[i].wheres_he) == 3:  # 3타자 중에서 정출을 두번 줌
                            jung_2times(workers, workers[i], max_place)
                            break
            else:  
              if len_outing >= 2:
                  for __ in range(poors):
                      for i in range(len(workers)):
                          if sum(workers[i].wheres_he) == 3 and workers[i].wheres_he[3] == 0:  # 3타자 중에서 정출을 두번 줌
                              jung_2times(workers, workers[i], max_place)
                              break
              else:
                  for __ in range(poors):
                      for i in range(len(workers)):
                          if sum(workers[i].wheres_he) == 3:  # 3타자 중에서 정출을 두번 줌
                              jung_2times(workers, workers[i], max_place)
                              break
            while True:
                workers_t = copy.deepcopy(workers)
                temp_jung_t = copy.deepcopy(temp_jung)
                max_place_t = copy.deepcopy(max_place_t)
                result=jung_rearrange(workers_t, temp_jung_t, max_place_t)
                if result == 0:
                  break
            

        elif int(sum([max_place[i][0] for i in range(4)])) < len(workers):  # 현 근무자가 타수보다 많을 경우
            no_jung = abs(int(sum([max_place[i][0] for i in range(4)])) - len(workers))
            temp_workers = workers[0:len(workers) - no_jung]

            while True:
                workers_t = copy.deepcopy(temp_workers)
                temp_jung_t = copy.deepcopy(temp_jung)
                max_place_t = copy.deepcopy(max_place)
                result=jung_rearrange(workers_t, temp_jung_t, max_place_t)
                if result == 0:
                  break
            

        # 정출 제외한 근무지 무한 루프
        workers = workers + outing
        real_workers = copy.deepcopy(workers)
        r_max_place = copy.deepcopy(max_place)
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
                real_workers = copy.deepcopy(workers)
                r_max_place = copy.deepcopy(max_place)
                count += 1  # w
                deter = 0
                if count == 500:
                    escape = False  # count가 적당히 커지면 어차피 안되는 거니까 함수 처음부터 다시 돌리기
                    break
        if escape == True:
            break

    return real_workers


def whatis_hwork(mat):
    if 1 in mat[0]:
        if 1 == mat[0][0]:
            print(Timetable[which_group][0][0], "-정출", end=' ')
        if 1 == mat[0][1]:
            print(Timetable[which_group][0][1], "-정출", end=' ')
        if 1 == mat[0][2]:
            print(Timetable[which_group][0][2], "-정출", end=' ')
        if 1 == mat[0][3]:
            print(Timetable[which_group][0][3], "-정출", end=' ')
    if 1 in mat[1]:
        if 1 == mat[1][0]:
            print(Timetable[which_group][0][0], "-별정", end=' ')
        if 1 == mat[1][1]:
            print(Timetable[which_group][0][1], "-별정", end=' ')
        if 1 == mat[1][2]:
            print(Timetable[which_group][0][2], "-별정", end=' ')
        if 1 == mat[1][3]:
            print(Timetable[which_group][0][3], "-별정", end=' ')
    if 1 in mat[2]:
        if 1 == mat[2][0]:
            print(Timetable[which_group][0][0], "-별후", end=' ')
        if 1 == mat[2][1]:
            print(Timetable[which_group][0][1], "-별후", end=' ')
        if 1 == mat[2][2]:
            print(Timetable[which_group][0][2], "-별후", end=' ')
        if 1 == mat[2][3]:
            print(Timetable[which_group][0][3], "-별후", end=' ')
    if 1 in mat[3]:
        if 1 == mat[3][0]:
            print(Timetable[which_group][0][0], "-서남문", end=' ')
        if 1 == mat[3][1]:
            print(Timetable[which_group][0][1], "-서남문", end=' ')
        if 1 == mat[3][2]:
            print(Timetable[which_group][0][2], "-서남문", end=' ')
        if 1 == mat[3][3]:
            print(Timetable[which_group][0][3], "-서남문", end=' ')
    print()

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

def jung_2times(workers, poor_man, max_place):
    place_number = [1, 2, 3]
    unlucky = poor_man.wheres_he[:]
    max_place[unlucky.index(1)][0] -= 1  # unluck.index(1)은 첫번째 근무 시간
    poor_man.work[0][unlucky.index(1)] = 1
    unlucky.remove(1)
    a = random.choice(place_number)
    max_place[unlucky.index(1) + 1][a] -= 1
    poor_man.work[a][unlucky.index(1) + 1] = 1
    unlucky.remove(1)
    max_place[unlucky.index(1) + 2][0] -= 1
    poor_man.work[0][unlucky.index(1) + 2] = 1
    # print(workers[i].work, end="\n")
    print(poor_man.name, end=' ')
    whatis_hwork(poor_man.work)
    workers.remove(poor_man)


def jung_rearrange(workers, temp_jung ,max_place):
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
        if check[3-i] < 0:  # 지금 시간대에 배치된 사람이 만약 최대 정출 타수를 초과한다면 음수 이므로 if돌린다
            for j in range(abs(check[3-i])):  # 넘은 사람만큼 빼내야 하므로 넘은 사람만큼 루프를 돌린다. 음수를 넣을순 없으니 절댓값
                while True:
                    poor_man = random.choice(temp_jung[3-i])  # 지금 시간대에서 랜덤으로 한명을 뽑는다.
                    if work_group[which_group] == 'B':
                        wheres_he = [poor_man.wheres_he[start + 0], poor_man.wheres_he[start + 1]]
                        x = [a for a, t in enumerate(wheres_he) if t == 1]
                        y = [b for b, t in enumerate(check) if t > 0]
                    else:
                        x = [a for a, t in enumerate(poor_man.wheres_he) if t == 1]  # 해당 시간 외에 다른 근무 시간 위치 반환
                        y = [b for b, t in enumerate(check) if t > 0]  # 현재 자리가 남는 근무 시간 위치를 반환, 저장
                    intersect = list(set(x).intersection(set(y)))  # 뽑힌 사람이 들어가지 않은 근무 시간과, 현재 자리가 남는 근무시간의 교집합을 찾는다
                    if intersect != []:  # 만약 교집합의 자리가 있다면 그 곳으로 뽑힌 사람을 넣는다. 아니면 위 x,y조건에 충족하는 사람을 while 루프로 다시 찾는다.
                        poor_man.wheres_he[intersect[0]+start] = 0
                        poor_man.wheres_he[3-i + start] = 1
                        temp_jung[3-i + start].remove(poor_man)
                        temp_jung[intersect[0]+start].append(poor_man)
                        max_place[3-i+start][0]+=1
                        max_place[intersect[0]+start][0]-=1
                        poor_man.work[0][3-i+start]=0
                        poor_man.work[0][intersect[0]+start]=1
                        check[3-i+start]+=1
                        check[intersect[0]+start]-=1
                        break
                    else:
                        continue
    check = []
    for i in range(4):
        check.append(max_place[i][0])

    print(check)



def schedule_place(workers,outing):
    while True:
        count = 0
        workers=lets_make_rank(workers)
        outing=lets_make_rank(outing)
        len_outing=len(outing[:])
        max_place = placetable[which_group][is_weekend - 1]
        deter = 0
        escape = True
        temp_jung=[[],[],[],[]] #정출에 들어가는 사람 리스트
        if work_group[which_group]=='B':  #외출자 수 계산 후 정출 들어갈 외출자 pick
            if len(outing)<=4:
                workers = workers+outing
                outing = []

            else:
                workers = workers+outing[0:4]
                outing = outing[4:]
        else:
            if len(outing)<=2:
                workers = workers + outing
                outing = []

            else:
                workers = workers + outing[0:2]
                outing = outing[2:]

        if int(sum([max_place[i][0] for i in range(4)])) >= len(workers):# 현 근무자수보다 정출 타수가 많거나 같을 경우
            poors = abs(int(sum([max_place[i][0] for i in range(4)])) - len(workers))
            if len_outing>=2:
                for __ in range(poors):
                    for i in range(len(workers)):
                        if sum(workers[i].wheres_he) == 3 and workers[i].wheres_he[3]==0:  # 3타자 중에서 정출을 두번 줌
                            jung_2times(workers, workers[i], max_place)
                            break
            else:
                for __ in range(poors):
                    for i in range(len(workers)):
                        if sum(workers[i].wheres_he) == 3:  # 3타자 중에서 정출을 두번 줌
                            jung_2times(workers, workers[i], max_place)
                            break

            jung_rearrange(workers, temp_jung, max_place)

        elif int(sum([max_place[i][0] for i in range(4)])) < len(workers): #현 근무자가 타수보다 많을 경우
            no_jung= abs(int(sum([max_place[i][0] for i in range(4)])) - len(workers))
            temp_workers = workers[0:len(workers)-no_jung]


            jung_rearrange(temp_workers, temp_jung, max_place)

        # 정출 제외한 근무지 무한 루프
        workers = workers + outing
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
                if count == 500:
                    escape=False  #count가 적당히 커지면 어차피 안되는 거니까 함수 처음부터 다시 돌리기
                    break
        if escape==True:
            break



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
    print()'''