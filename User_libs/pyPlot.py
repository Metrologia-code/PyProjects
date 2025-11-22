import matplotlib.pyplot as plt

class PlotterClass():

    def __init__(self, y_names, x_label='x', y_label='y', plot_name='Test', pts={}):

        self.pts=pts
        
        #интерактивный режим плота вкл
        plt.ion()
    
        colors = ['b', 'k', 'r', 'm', 'g', 'c',]
        #'linestyle':'solid', 'linewidth':0.3, 'marker':'.', 'markersize':1,
        #line_options = {'c':new_color}
    
        self.lines = {}
        self.xdata, self.ydata = [], {}
        
        self.fig, self.ax = plt.subplots(figsize=(8, 4))
        self.ax.set_title(label=plot_name, fontname='Arial', fontsize=12, )
        self.ax.set_xlabel(xlabel=x_label, fontname='Arial', fontsize=12, )
        self.ax.set_ylabel(ylabel=y_label, fontname='Arial', fontsize=12, )
        if self.pts:
            self.x_step, self.x_pts = self.pts['x_step'], self.pts['x_pts']
            self.ax.set_xlim([0, self.x_step * self.x_pts])
    
        for name in y_names:
            self.lines[name], = self.ax.plot([], [], c=colors[y_names.index(name)], label=name)
            self.ydata[name] = []
    
        plt.show()


    def plot_routine(self, i, x, results, ):

        #добавляем значение x к массиву
        self.xdata.append(x)

        #удаляем "убежавшее" значение x и обновляем лимиты оси
        if self.pts:
            if i+1 > self.x_pts:
                self.xdata = self.xdata[1:]
                xmin, xmax = min(self.xdata), max(self.xdata)
                self.ax.set_xlim(xmin, xmax)

        #итерируем линии
        for name, line in self.lines.items():
            
            #добавляем измеренное значение y в линию
            self.ydata[name].append(results[name])

            #удаляем "убежавшее" значение y
            if self.pts:
                if i+1 > self.x_pts:
                    self.ydata[name] = self.ydata[name][1:]
            
            #записываем списки данных с обновленными значениями в плот
            line.set_ydata(self.ydata[name])
            line.set_xdata(self.xdata)

        #лимиты осей
        self.ax.relim()
        self.ax.autoscale_view()
        #создаем/обновляем легенду
        self.ax.legend(loc='best', fontsize='x-small', markerscale=2.5)
        #перерисовываем плот
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()


    def save_figure(self, file_path, ):

        plt.savefig(file_path+'.png')

        