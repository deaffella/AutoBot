

Робот -> Комп

    rsync -rv --progress --partial nano@192.168.2.220:/home/nano/deaffy/AutoBot/donkey_car ~/projects/autobot/


Комп -> Робот
    
    rsync -rv --progress --partial ~/projects/autobot/donkey_car/models/ nano@192.168.2.220:/home/nano/deaffy/AutoBot/donkey_car/models/