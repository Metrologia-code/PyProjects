from StepMotor_libs import StepMotor, RunCommand

with StepMotor(host="192.168.88.13", port=8234) as motor:
    print(f'Cтатус мотора:\n{motor.status}\n')
    print(f'Мотор занят: {motor.status.busy}')
    print(f'Мотор движется: {motor.status.moving}')
    print(f'Положение: {motor.current_position} микрошагов')
    print(f'Дробление шага: 1/{2 ** motor.u_step}')
    print(f'Направление {"прямое" if motor.direction else "обратное"}')
    print(f'Целевая позиция: {motor.target_position} микрошагов')
    print(f'Значение CMD-регистра: {motor.command.name}')
    # motor.set_data_time()
    print(f'Системные (SMSD-4.2) дата и время: {motor.get_data_time().strftime("%d.%m.%Y %H:%M:%S")}')
    print()

    # Сбрасываем текущую позицию
    motor.reset_current_position()
    home_pos = motor.current_position
    print(f'Текущая позиция {home_pos} микрошагов.')

    # Запрашиваем дробление шага и считаем позиции куда хотим приехать (400 полных шага - 1 оборот)
    u_steps_per_step = 2 ** motor.u_step
    pos1 = home_pos + 400 * u_steps_per_step
    pos2 = home_pos - 400 * u_steps_per_step

    if home_pos is not None and home_pos == 0:
        # Едем в первую точку
        print(f'Едем в позицию {pos1} микрошагов')
        motor.go_to(pos1)
        print(f'Текущая позиция {motor.current_position} микрошагов.')
        print()

        # Едем во вторую точку
        print(f'Едем в позицию {pos2} микрошагов')
        motor.go_to(pos2)
        print(f'Текущая позиция {motor.current_position} микрошагов.')
        print()

        # Едем в исходное состояние
        print(f'Едем в позицию {home_pos} микрошагов')
        motor.go_home()
        print(f'Текущая позиция {motor.current_position} микрошагов.')
        print()

        # Внутренняя программа использует значение RUN в CMD-регистре и если видит, что значение изменилось,
        # приостанавливает работу. Для продолжения корректной работы внутренней программы надо вернуть значение
        # RUN в CMD-регистр.
        motor.command = RunCommand.RUN

        print(f'Текущее значение CMD-регистра: {motor.command.name}')
