import sys
import numpy as np


class TaskFileParser:
    ''' Парсер файла-задания для axes_scanner.

        Формат: первая непустая строка - заголовок (может начинаться с '#'),
        имена столбцов разделяются табуляцией. Данные сопоставляются со
        столбцами ПО ИМЕНАМ, поэтому порядок столбцов произвольный, а новые
        столбцы можно добавлять в середину и в конец без поломки парсинга.

        Обязательные столбцы: все оси (по умолчанию APT/APL/APR/APB) и intvls.
        Необязательные: post_delay, filename, x_axis.
        Неизвестные столбцы игнорируются с предупреждением.
    '''

    #Имена осей по умолчанию (порядок задаёт номера осей для контроллера)
    AXES = ['APT', 'APL', 'APR', 'APB']

    #Алиасы имён столбцов: в нижнем регистре -> каноническое имя
    FIELD_ALIASES = {
        'intvls': 'intvls',
        'intervals': 'intvls',
        'post_delay': 'post_delay',
        'postdelay': 'post_delay',
        'filename': 'filename',
        'x_axis': 'x_axis',
        'xaxis': 'x_axis',
        'x': 'x_axis',
    }

    def __init__(self, axes=None):
        self.axes_names = list(axes) if axes else list(self.AXES)
        #Собираем карту канонических имён: регистронезависимо
        self.canonical = {name.lower(): name for name in self.axes_names}
        self.canonical.update(self.FIELD_ALIASES)

    #---ОСНОВНОЙ ВХОД---
    def parse(self, task_filename):
        with open(task_filename, "r", encoding="utf-8") as file:
            lines = file.readlines()

        header_index, columns, unknown = self._read_header(lines, task_filename)
        if unknown:
            print(f"[WARNING] Файл задания '{task_filename}': "
                  f"неизвестные столбцы проигнорированы: {', '.join(unknown)}")

        ALL_TASKS = []
        for index in range(header_index + 1, len(lines)):
            line = lines[index].split('#')[0].strip()
            if not line:
                continue
            ALL_TASKS.append(self._parse_row(line, columns, index + 1, task_filename))
        return ALL_TASKS

    #---ЗАГОЛОВОК---
    def _read_header(self, lines, task_filename):
        header_index = None
        for index, line in enumerate(lines):
            if line.strip():
                header_index = index
                break
        if header_index is None:
            self._error(task_filename, None, "файл пуст, не найден заголовок")

        header_text = lines[header_index].strip()
        if header_text.startswith('#'):
            header_text = header_text.lstrip('#').strip()
        raw_names = [name.strip() for name in header_text.split('\t')]

        columns = []
        unknown = []
        for raw_name in raw_names:
            canonical = self.canonical.get(raw_name.lower())
            if canonical is None:
                unknown.append(raw_name)
            else:
                if canonical in columns:
                    self._error(task_filename, header_index + 1,
                                f"столбец '{canonical}' указан несколько раз")
                columns.append(canonical)

        required = self.axes_names + ['intvls']
        missing = [name for name in required if name not in columns]
        if missing:
            self._error(task_filename, header_index + 1,
                        f"в заголовке отсутствуют обязательные столбцы: {', '.join(missing)}")
        return header_index, columns, unknown

    #---СТРОКА ДАННЫХ---
    def _parse_row(self, line, columns, line_number, task_filename):
        cells = [cell.strip() for cell in line.split('\t')]
        #Недостающие ячейки считаем пустыми
        cells += [''] * (len(columns) - len(cells))
        row = {columns[i]: cells[i] for i in range(len(columns))}
        intervals = self._parse_intervals(row, line_number, task_filename)

        #Оси: start:end или одиночное значение
        axes = []
        for number, axis_name in enumerate(self.axes_names):
            value = row[axis_name]
            if not value:
                self._error(task_filename, line_number, f"не задано значение оси {axis_name}")
            start, end = self._parse_axis_values(value, axis_name, line_number, task_filename)
            axes.append({
                'name': axis_name,
                'number': number,
                'start': start,
                'end': end,
                'pos': np.linspace(start, end, intervals + 1),
                'is_used': (start != end),
            })

        post_delay = self._parse_post_delay(row, line_number, task_filename)
        filename = row['filename'].strip() if 'filename' in row else ''
        x_axis = self._parse_x_axis(row, line_number, task_filename)

        return {
            'axes': axes,
            'intervals': intervals,
            'post_delay': post_delay,
            'filename': filename,
            'x_axis': x_axis,
        }

    def _parse_intervals(self, row, line_number, task_filename):
        value = row.get('intvls', '')
        if not value:
            self._error(task_filename, line_number, "не задано число интервалов (intvls)")
        try:
            intervals = int(value)
        except ValueError:
            self._error(task_filename, line_number, f"неверное число интервалов: '{value}'")
        if intervals < 1:
            self._error(task_filename, line_number, f"число интервалов должно быть >= 1, получено {intervals}")
        return intervals

    def _parse_axis_values(self, value, axis_name, line_number, task_filename):
        parts = value.split(':')
        if len(parts) == 1:
            start = end = parts[0]
        elif len(parts) == 2:
            start, end = parts
        else:
            self._error(task_filename, line_number,
                        f"неверное значение оси {axis_name}: '{value}' (ожидается start:end или число)")
        try:
            return float(start), float(end)
        except ValueError:
            self._error(task_filename, line_number,
                        f"неверное значение оси {axis_name}: '{value}' (ожидается start:end или число)")

    def _parse_post_delay(self, row, line_number, task_filename):
        value = row.get('post_delay', '')
        if not value:
            return 0.0
        try:
            return float(value)
        except ValueError:
            self._error(task_filename, line_number, f"неверная задержка post_delay: '{value}'")

    def _parse_x_axis(self, row, line_number, task_filename):
        value = row.get('x_axis', '')
        if not value:
            return None
        if value.lower() == 'time':
            return 'time'
        for axis_name in self.axes_names:
            if value.lower() == axis_name.lower():
                return axis_name
        self._error(task_filename, line_number,
                    f"неизвестная ось X '{value}' (допустимо: time или {', '.join(self.axes_names)})")

    #---ОШИБКИ---
    @staticmethod
    def _error(task_filename, line_number, message):
        location = f", строка {line_number}" if line_number else ""
        print(f"\n[ОШИБКА]: Файл задания '{task_filename}'{location}: {message}")
        sys.exit(1)
