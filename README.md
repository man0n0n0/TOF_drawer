# hardwr
**cad**
- [x] design bracket nema 23
  - [x] TODO : v0.1 meutriere pour belt tentionning 
  - courroie à fleur du tirroir : h etalon boite rouge == 61 mm
  - large poulie GT5 od : 44mm
- [ ] design porte poulie
  - [ ] TODO : include rondelle side around bearing
- [x] design tiroir / poulie
  - GT5 11m large
  - poulie : 16.56 * 19.9
    
**kinetic**
- [ ] TODO : microstepping adjustment

**electronic**
- [ ] TODO : add button : EXTERNAL_BOOT + NETWORK_ACTIVATION 


# softwr
- boot :
  - if button x pressed : enable network + http

- __main__.py :
  - stepper management
    - [ ] TODO : acceleration management (using AccelStepper ? https://github.com/pedromneto97/AccelStepper-MicroPython/blob/master/AccelStepper.py)

  - client interface variables :
    - distance de detection
    - vitesse sortie / entrée tiroir
