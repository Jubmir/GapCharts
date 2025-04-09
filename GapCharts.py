from glob import glob
import os
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from math import sqrt, exp
from scipy import integrate
from statistics import stdev, mean
from threading import Thread
from time import sleep
import tkinter as tk
import random

def readline_tsv(open_file):
    x = open_file.readline()
    values = x.strip().split('\t')
    return values

def read_tsv(file_name, enc):
    values = []
    with open(file_name, 'r', newline='', encoding=enc) as file:
        lines = file.readlines()
        for line in lines:
            values.append(line.strip().split('\t'))
    return values

def newest_folder(path):
    folder = None 
    iterator = os.scandir(path)
    l = []
    l2 = []
    for item in iterator:
        l.append(item.path)
    for folder in l:
        l2 += glob(folder+"/*.txt")
    temp = max(l2, key=os.path.getmtime)
    for item in l:
        if item in temp:  
            folder = item
            print(f"Znaleziono folder {folder}")
        else:
            print("Nieznaleziono folderu")
    return folder

def open_newest_file(folder, keyword, enc):
    files = glob(folder+"/*.txt")
    for file in files:
        print(f"Znaleziono plik {file}")
        if keyword not in file:
            files.remove(file)     
    return open(max(files, key=os.path.getmtime),'r',encoding=enc)

def offset_search(string, keyword, offset1, offset2):
    pos = string.find(keyword)
    if pos == -1:
        raise ValueError(f"'{keyword}' not in string ")
    datum = string[pos+offset1:pos+offset2]
    return datum

def probden(x, stdev, mean):
    if stdev == 0 or mean == 0:
         raise ValueError("stdev and mean must be nonzero")
    else:
        i1 = 1/(stdev*sqrt(6.283))
        i2 = -(x-mean)**2
        i3 = 2*stdev**2
        return i1*exp(i2/i3)

class Chart:
    def __init__(self, gapnum, master_frame, ylabel, data_position1, data_position2):
        self.gapnum = gapnum
        self.chart = Figure(figsize=(6.3,1.1), dpi=100)
        self.canv = FigureCanvasTkAgg(self.chart, master=master_frame)
        self.op_side = []
        self.machine_side = []
        self.column = None
        self.row = None
        self.plot = self.chart.add_subplot(111)      
        self.pd = 0
        self.diff = 0
        self.ylabel = ylabel
        self.data_position1 = data_position1
        self.data_position2 = data_position2
        
    def get_data(self, values):
        try:
            self.machine_side.append(float(values[self.data_position1][:6]))
            self.op_side.append(float(values[self.data_position2][:6]))
            print(f"M: {values[self.data_position1]} O: {values[self.data_position2]}")
            print(self.machine_side[len(self.machine_side)-1])
        except ValueError or IndexError:
            print("błędne dane")
            with open("log.txt", mode = 'a') as log:
                log.write(f"{values}")
    
    def ini(self):
        self.canv.get_tk_widget().grid(column=self.column, row=self.row)
               
    def config(self):
        self.plot.cla()
        self.plot.set_xticks([])
        self.plot.set_ylabel(f"{self.ylabel} {self.gapnum}",fontsize = 10)

    def defect_probability(self, o_lowerlimit, o_upperlimit, m_lowerlimit, m_upperlimit):               
        try:
            x1 = integrate.quad(probden, o_lowerlimit, o_upperlimit, args=(stdev(self.op_side), mean(self.op_side)))[0]
            x2 = integrate.quad(probden, m_lowerlimit, m_upperlimit, args=(stdev(self.machine_side), mean(self.machine_side)))[0]
            print("pd :"+str(1-x1))
            print("pd :"+str(1-x2))
            if x1 > x2:
                 self.pd = abs(1-x1)
            else:
                 self.pd = abs(1-x2)
        except ValueError:
            self.pd = 0

    def reset(self):
        self.machine_side.clear()
        self.op_side.clear()
        self.pd = 0
        self.draw()
        
class GapChart(Chart):
    def __init__(self, gapnum, nominal, neg_tol, pos_tol, master_frame, data_position1, data_position2):
        super().__init__(gapnum, master_frame, "Gap ",  data_position1, data_position2)
        self.nominal = float(nominal)
        self.lowerlimit = float(self.nominal) - float(neg_tol)
        self.upperlimit = float(self.nominal) + float(pos_tol)
       
    def avdiff(self):
        try:
            av = (mean(self.op_side)+mean(self.machine_side))/2
            self.diff =  av - self.nominal
        except:
            self.diff = 0

    def draw(self):
        super().config()
        self.plot.set_ylabel('Gap '+str(self.gapnum))
        self.avdiff()
        self.defect_probability()
        self.plot.set_xlabel("Diff: "+str(self.diff)[:4]+"   "+"PD : "+str((self.pd)*100)[:5]+'%', labelpad=-11)
        self.plot.set_yticks([self.lowerlimit, self.nominal ,self.upperlimit])
        self.plot.set_ylim(self.lowerlimit-1, self.upperlimit+1)
        if len(self.machine_side) < 50:
            self.plot.plot(self.machine_side, 'green', linewidth = 1)
            self.plot.plot(self.op_side, 'magenta', linewidth = 1)    
        else:
            self.plot.plot(self.machine_side[len(self.machine_side)-50:], 'green')
            self.plot.plot(self.op_side[len(self.op_side)-50:], 'magenta')    
        self.plot.axhline(y=(self.lowerlimit+self.upperlimit)/2, ls = ":", color='y', linewidth=1)
        self.plot.axhline(y=(self.lowerlimit), ls = ":", color='r', linewidth=1)
        self.plot.axhline(y=(self.upperlimit), ls = ":", color='r', linewidth=1)
        self.canv.draw()
        del self.op_side[:len(self.op_side)-50], self.machine_side[:len(self.machine_side)-50]
                
    def defect_probability(self):
        super().defect_probability(self.lowerlimit, self.upperlimit, self.lowerlimit, self.upperlimit)

    def reset(self):
        self.machine_side.clear()
        self.op_side.clear()
        self.pd = 0
        self.draw()
        
class YChart(Chart):
    def __init__(self, gapnum, m_nominal, o_nominal, offset, typecolor, limits, master_frame, data_position1 = 21, data_position2 = 25):
        super().__init__(gapnum,  master_frame, "Gap Y ", data_position1, data_position2)
        self.typecolor = typecolor
        self.m_nominal = float(m_nominal)
        self.o_nominal = float(o_nominal)
        self.limits = []
        self.ticks = []
        self.offset = float(offset)
        for l in limits:
            self.limits.append(float(l))
        for l in self.limits:
            if l < 0:
                self.ticks.append(l+self.offset)
            else:
                self.ticks.append(l-self.offset)

    def get_data(self, values):
        try:
            self.machine_side.append(-float(values[self.data_position1][:4])+self.offset)
            self.op_side.append(float(values[self.data_position2][:4])-self.offset)
            print(f"M: {values[self.data_position1]} O: {values[self.data_position2]}")
            print(self.machine_side[len(self.machine_side)-1])
        except ValueError or IndexError:
            print(f"Błędne dane {values}")
            with open("log.txt", mode = 'a') as log:
                log.write(f"{values} \n")
    
    def draw(self):
        super().config()
        #self.plot.set_xlabel("Diff: "+str(self.diff)[:4]+"   "+"PD : "+str((self.pd)*100)[:5]+'%', labelpad=-11)
        self.plot.set_yticks(self.ticks)
        self.plot.set_yticklabels([])
        self.plot.set_ylim(self.ticks[0]-0.5, self.ticks[3]+0.5)
        if len(self.machine_side) < 50:
            self.plot.plot(self.machine_side, 'green', linewidth = 1)
            self.plot.plot(self.op_side, 'magenta', linewidth = 1)  
        else:
            self.plot.plot(self.machine_side, 'purple', linewidth = 1)
            self.plot.plot(self.op_side, 'purple', linewidth = 1)   
        self.plot.axhline(y=self.m_nominal-self.offset, ls = ":", color='y', linewidth=1)
        self.plot.axhline(y=self.o_nominal+self.offset, ls = ":", color='y', linewidth=1)
        for tick in self.ticks:
            self.plot.axhline(y=tick, ls = ":", color=self.typecolor, linewidth=1)
        self.canv.draw()
        del self.machine_side[:len(self.machine_side)-50]
        del self.op_side[:len(self.op_side)-50]

    def nondefectprob(self):
        super().nondefectprob(self, self.limits[0], self.limits[1], self.limits[2], self.limits[3])
        print(f"ypd: {self.pd}")
        
class VoidGap:
    def __init__(self,gapnum):
        self.gapnum = gapnum
        self.op_side = []
        self.machine_side = []
        self.typ = 'x'
        self.data = []
    def ini(self):
        pass
    def draw(self):
        pass
    def get_data(self, values):
        pass
    def nondefectprob(self):
        pass
    def avdiff(self):
        pass
    def reset(self):
        pass
    
class ChartApp:
    def __init__(self, _title, top_text, is_root = 1, do_stats = 1):
        if is_root:
            self.root=tk.Tk()
        else:
            self.root = tk.Toplevel()
        self.top_frame = tk.Frame(self.root)
        self.main_frame = tk.Frame(self.root, bg = 'white')
        self.bot_frame = tk.Frame(self.root)
        self.top_label = tk.Label(self.top_frame, text = top_text, font=('font',20)).pack(side = "left")
        self.bot_label1 = tk.Label(self.bot_frame, text = "- Strona Maszyny -",font=('font',13), fg = 'green')
        self.bot_label2 = tk.Label(self.bot_frame, text = "- Strona Operatora -" ,font=('font',13), fg='magenta') 
        self.top_frame.pack(fill = tk.X)
        self.main_frame.pack(expand = True, fill = tk.BOTH)
        self.bot_frame.pack()
        def reset_func():
            for obj in self.charts:
                obj.reset()
        self.charts = [] 
        self.reset_button = tk.Button(self.top_frame, text='Reset', command = reset_func, font=('font', 13)).pack(side="right",padx=10)
        self.bot_label1.pack()
        self.bot_label2.pack()  
        self.info1_var = tk.StringVar()
        self.info2_var = tk.StringVar()
        self.info1 = tk.Label(self.top_frame, textvariable = self.info1_var, font=('font',16)).pack(side = 'right')
        if do_stats:
            self.info1_1 = tk.Label(self.top_frame, text="stdevSMA =",font=('font',15)).pack(side='right')
            self.info2 = tk.Label(self.top_frame, textvariable = self.info2_var, font=('font',16)).pack(side='right')
            self.info2_1 = tk.Label(self.top_frame, text="Średnie różnice: ", font=('font',15)).pack(side='right')
        self.root.title(_title)
         
    def init_charts(self):
         c = 0
         r = 0 
         for obj in self.charts:
             if c > 1:
                 c = 0
                 r += 1
             obj.column = c
             obj.row = r
             c += 1
             obj.ini()
             obj.draw()
             
    def xdiff(self):
        f = 1
        b = 2
        front = 0
        back = 0
        while f < 17:
            front += self.charts[f].diff
            f+=2
        while b < 16:
            back += self.charts[b].diff
            b+=2
        front /= 8
        back /= 7 
        return front, back 
   
    def avstdv(self):
        a = 0
        for obj in self.charts[:len(self.charts)-1]:
            try:
                a += stdev(obj.machine_side)
                a += stdev(obj.op_side)
            except:
                pass
        return a / 32
        
    def stat_loop(self):
        while True:
            self.info2_var.set("Front = "+str(self.xdiff()[0])[:4]+", "+"Back = "+str(self.xdiff()[1])[:4]+" ")
            self.info1_var.set(str(self.avstdv())[:5])
            sleep(1)
        
class DataFeeder:
    def __init__(self, master_path, target_lists, index_position, fake_mode=False):
        self.master_path = master_path
        self.folder = None 
        self.file = None
        self.error_count = 0
        self.target_lists = target_lists
        self.index_position = index_position
        self.fake_mode = fake_mode
        self.counter = 0  # tylko w trybie fake
    
    def ini(self):
        if not self.fake_mode:
            self.folder = newest_folder(self.master_path)
            self.file = open_newest_file(self.folder, "Gap", "utf-16")
            self.file.readlines()
        
    def _generate_fake_data(self):
        index = self.counter % 16 + 1
        self.counter += 1
        fake_values = [''] * 30
        fake_values[10] = f"Gap{index:02}"  # Index GAP
        fake_values[13] = f"{random.uniform(3.5, 5.3):.3f}"  # Machine Side
        fake_values[17] = f"{random.uniform(3.5, 5.3):.3f}"  # Operator Side
        fake_values[21] = f"{random.uniform(1.1, 1.3):.3f}"  # Y Machine
        fake_values[25] = f"{random.uniform(1.1, 1.3):.3f}"  # Y Operator
        return index, fake_values
    
    def give_data(self):
        while True:
            if self.fake_mode:
                index, values = self._generate_fake_data()
                for l in self.target_lists:
                    try:
                        l[index-1].get_data(values)
                        l[index-1].draw()
                    except IndexError:
                        pass
            else:
                if self.error_count > 100:
                    self.ini()
                    self.error_count = 0
                else:
                    values = readline_tsv(self.file)
                    if any(values): 
                        self.error_count = 0
                        try:
                            index = int(offset_search(values[self.index_position], "Gap", 3, 7))
                            for l in self.target_lists:
                                l[index-1].get_data(values)
                                l[index-1].draw()
                        except IndexError:
                            self.error_count += 1
                    else:
                        self.error_count += 1
            sleep(0.1)       
            
def main():
    #MASTERPATH = "E:/Univision/ProInspect34/History/"
    MASTERPATH  = "test_data/"
    Gap = ChartApp("GapCharts", "GapCharts")
    Y = ChartApp("YCharts","YCharts", is_root = 0, do_stats = 0)
    gap_recipe = read_tsv("Gap Recipe.tsv", 'utf-8')
    y_recipe = read_tsv("Y Recipe.tsv", 'utf-8')

    i = 1 
    while i < len(gap_recipe):
        Gap.charts.append(GapChart(gap_recipe[i][0], gap_recipe[i][1], gap_recipe[i][2], gap_recipe[i][3], Gap.main_frame, 13, 17))
        i += 1
    
    j = 1
    i = 1
    while i < len(Gap.charts):
        while j < 2:
            Y.charts.append(YChart(i, y_recipe[4][0], y_recipe[4][1], y_recipe[4][2], y_recipe[4][3], y_recipe[5], Y.main_frame))
            j += 1
            i += 1
        while j < 4:
            Y.charts.append(YChart(i, y_recipe[1][0], y_recipe[1][1], y_recipe[1][2], y_recipe[1][3], y_recipe[2], Y.main_frame))
            j += 1
            i += 1
        if j == 4:
            j = 0

    del i, j
                            
    Gap.charts.append(VoidGap(17))
    Y.charts.append(VoidGap(17))
    
    feeder = DataFeeder(MASTERPATH, [Gap.charts, Y.charts], 10, fake_mode=True)
    feeder.ini()
    
   
    Gap.init_charts()  
    Y.init_charts()    
    
    Thread(target = feeder.give_data).start()
    Thread(target = Gap.stat_loop).start()
    Gap.root.mainloop()
  
        
if __name__ == "__main__":
    main()
