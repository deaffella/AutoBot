

### WiFi powersave off
___
    
    https://github.com/robwaat/Tutorial/blob/master/Jetson%20Disable%20Wifi%20Power%20Management.md
    

### Sync Files
___


Робот -> Комп

    rsync -rv --progress --partial nano@192.168.2.220:/home/nano/deaffy/AutoBot/donkey_car/DYNAMIC_DATA/data .


Комп -> Робот
    
    rsync -rv --progress --partial ~/projects/autobot/donkey_car/models/ nano@192.168.2.220:/home/nano/deaffy/AutoBot/donkey_car/models/
    
___

You end up with a Linear.h5 in the models folder

    python3 manage.py train --model=./models/Linear.h5 --tub=./data/tub_1_19-06-29,...

(optional) copy `./models/Linear.h5` from your desktop computer to your Jetson Nano in your working dir (`~mycar/models/`)

Freeze model using `freeze_model.py` in `donkeycar/scripts` ; the frozen model is stored as protocol buffers.
This command also exports some metadata about the model which is saved in `./models/Linear.metadata`

    python3 freeze_model.py --model="./home_models/pilot_22-10-20_0.h5" --output="./home_models/frozen_model.pb"

Convert the frozen model to UFF. The command below creates a file ./models/Linear.uff

    python3 /usr/lib/python3.6/dist-packages/uff/bin/convert_to_uff.py frozen_model.pb