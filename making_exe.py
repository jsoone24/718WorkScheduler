import sys
from PyQt5.QtWidgets import *
from Main_program import *

class MyApp(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.acci = QLineEdit()
        self.acci.setPlaceholderText('사고자를 입력하세요')
        self.out = QLineEdit()
        self.out.setPlaceholderText('외출자를 입력하세요')
        self.out.returnPressed.connect(self.make_work)
        self.lbl = QLabel('근무결과')
        self.result = QTextEdit()

        grid = QGridLayout()
        grid.addWidget(self.acci, 0, 0)
        grid.addWidget(self.out, 1, 0)
        grid.addWidget(self.lbl, 2, 0)
        grid.addWidget(self.result, 2, 1)

        self.setLayout(grid)

        self.setWindowTitle('718근무 프로그램')
        self.setGeometry(100, 100, 700, 450)
        self.show()

    def make_work(self):
        Time_Scheduler.acci = self.acci.text()
        Time_Scheduler.out = self.out.text()
        self.scheduled_work, self.real_worker, self.outing = Time_Scheduler.scheduler(Timetable, which_group, work_group, is_weekend,
                                                                       p2)
        self.result.append(Time_Scheduler.today_group)
        self.result.append("총원 : ", str(len(p2)))
        '''
        print("사고자 수 : %d" % (len(accident)), "\n외출자 수 %d" % (len(outing)), "\n\n사고 내용\n사고자 : ",
              [x.name for x in accident], "\n외출자 : ", [x.name for x in outing])
        print("\n복귀타 없는 외출자 수 : %d" % (len(no_return_work)), "\n내용 : ", [x.name for x in no_return_work])
        print("\n현원 : %d" % len(real_worker))
        print("1타자 수 : %d" % len(hes_1), [x.name for x in hes_1])
        print("2타자 수 : %d" % len(hes_2), [x.name for x in hes_2])
        print("3타자 수 : %d" % len(hes_3), [x.name for x in hes_3])
        if today_group == 'B':
            print("긴밤자 수 : %d" % len(long_nighter), "긴밤자 : ", [x.name for x in long_nighter])
        for i in range(4):
            print(today_time[i], "\t", [x.name for x in temp_work[i]])
        while True:
            real_worker_t = copy.deepcopy(real_worker)
            outing_t = copy.deepcopy(outing)
            result = Work_Scheduler.schedule_place(real_worker_t, outing_t)
            if result != -1:
                break

        if result != -1:
            for h in result:
                print(h.name, end=' ')
                Work_Scheduler.whatis_hwork(h.work)
    '''





if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())
