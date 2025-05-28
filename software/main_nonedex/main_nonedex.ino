#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <AccelStepper.h>
#include <ld2410.h>
#include <ArduinoJson.h>
#include <SPIFFS.h>

// Stepper specific
#define STEP_PIN 33     
#define DIR_PIN 25
#define EN_PIN 26                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      
#define STEP_PER_MM 25.6  // 25.6 steps per mm

#define MONITOR_SERIAL Serial

// RADAR 1
#define RADAR1_SERIAL Serial1
#define RADAR1_RX_PIN 32
#define RADAR1_TX_PIN 12

// RADAR 2
#define RADAR2_SERIAL Serial2
#define RADAR2_RX_PIN 14
#define RADAR2_TX_PIN 27

// Button pin configuration
#define CONFIG_BUTTON_PIN 17  
#define ENDSWITCH_PIN 15

// Drawer specific
#define D_OUT 200
https://www.google.com/search?client=firefox-b-lm&channel=entpr&q=prise+choco
// Access Point credentials
const char* ap_ssid = "ESP32_Control";
const char* ap_password = "12345678";

// Variables to be modified via web interface
int D_THRESHOLD = 300;    // Default: 300cm
int BACK_SPEED = 8000;     // Default: 8000 steps/sec
int FORW_SPEED = 1000;     // Default: 1000 steps/sec
int WAIT_INSIDE = 3000;    // Default: 3000ms

// Operation mode flag
bool configMode = false;

// Create webserver on port 80
WebServer server(80);

// Preferences object for persistent storage
Preferences preferences;

// Create the stepper instance
AccelStepper stepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN);

// radar declaration
ld2410 radar1;
ld2410 radar2;

uint32_t r1_lastreading = 0;
volatile int radar1_d;
bool radar1Connected = false;

uint32_t r2_lastreading = 0;
volatile int radar2_d;
bool radar2Connected = false;

volatile int human_d;

bool isHomed = false;
bool IsOpen = true; //so that it engage homing at start

/*##################################################################################
SETUP LOOP
##################################################################################*/

void setup() {
  // Start serial for debugging
  // Initialize serial communication
  MONITOR_SERIAL.begin(115200); //Feedback over Serial Monitor
  MONITOR_SERIAL.println("Starting setup...");
  
  // Initialize button pin && endswitch
  pinMode(CONFIG_BUTTON_PIN, INPUT_PULLUP);
  pinMode(ENDSWITCH_PIN, INPUT_PULLUP);
  
  // Load saved values (needed in both modes)
  loadSavedValues();
  
  // Check if button is pressed at startup
  if (digitalRead(CONFIG_BUTTON_PIN) == LOW) {
    MONITOR_SERIAL.println("Config button pressed - entering configuration mode");
    configMode = true;
    
    // Set up ESP32 as an Access Point
    WiFi.mode(WIFI_AP);
    WiFi.softAP(ap_ssid, ap_password);
    
    // Define server endpoints
    server.on("/", HTTP_GET, handleRoot);
    server.on("/", HTTP_POST, handleFormSubmission);
    
    // Start the server
    server.begin();
  } else {
    configMode = false;

    // Configure the stepper
    stepper.setPinsInverted(false);
    stepper.setMaxSpeed(15000);
    stepper.setAcceleration(10000);
    pinMode(EN_PIN, OUTPUT);
    digitalWrite(EN_PIN, LOW); 
  
    //radar1 initialisation
    RADAR1_SERIAL.begin(256000, SERIAL_8N1, RADAR1_RX_PIN, RADAR1_TX_PIN); //UART for monitoring the radar
    delay(500);
   
    if(radar1.begin(RADAR1_SERIAL))
    {
      MONITOR_SERIAL.println(F("OK"));
    }
    else
    {
      MONITOR_SERIAL.println(F("not connected"));
    }
    
    //radar2 initialisation
    RADAR2_SERIAL.begin(256000, SERIAL_8N1, RADAR2_RX_PIN, RADAR2_TX_PIN); //UART for monitoring the radar
    delay(500);
   
    if(radar2.begin(RADAR2_SERIAL))
    {
      MONITOR_SERIAL.println(F("OK"));
    }
    else
    {
      MONITOR_SERIAL.println(F("not connected"));
    }
    
    Serial.println("Setup complete");
   
  }
}

/*##################################################################################
MAIN LOOP
##################################################################################*/

void loop() {
  if (configMode) 
  {
    // Handle client requests in configuration mode
    server.handleClient();
  } 
  else 
  {
    // Radar1 mesurement logic
    radar1.read();
    
    if(radar1.isConnected() && millis() - r1_lastreading > 20)  //Report every 20ms
    {
      r1_lastreading = millis();                                            
      if(radar1.movingTargetDetected())
      {
        radar1_d = radar1.movingTargetDistance();
        //MONITOR_SERIAL.println(radar1_d);
      }
    }
  
    // Radar2 mesurement logic
    radar2.read();
    
    if(radar2.isConnected() && millis() - r2_lastreading > 20)  //Report every 20ms
    {
      r2_lastreading = millis();
      if(radar2.movingTargetDetected())
      {
        radar2_d = radar2.movingTargetDistance();
        //MONITOR_SERIAL.println(radar2_d);
      }
    }
  
    // Presence value math operation
    human_d = min(radar1_d,radar2_d);
    //MONITOR_SERIAL.println(human_d);
    //MONITOR_SERIAL.println(D_THRESHOLD);
    
    if (human_d < D_THRESHOLD && IsOpen) {
      digitalWrite(EN_PIN, LOW); //enable stepper
      
      // Move BACKWARD 
      stepper.setMaxSpeed(BACK_SPEED);
      stepper.moveTo(10 * STEP_PER_MM);
      stepper.runToPosition(); // (blocking)

      if (!isHomed)
      {      
        while (digitalRead(ENDSWITCH_PIN)) 
        {    
          digitalWrite(DIR_PIN, LOW);      // (HIGH = anti-clockwise / LOW = clockwise)
          digitalWrite(STEP_PIN, HIGH);
          delay(5);                         // Delay to slow down speed of Stepper
          digitalWrite(STEP_PIN, LOW);
          delay(5);    
        } 
        
        stepper.setCurrentPosition(0);
        stepper.moveTo(1 * STEP_PER_MM);
        stepper.runToPosition(); // (blocking)
        
        delay(WAIT_INSIDE);
        //MONITOR_SERIAL.println("homed ! wainting inside");
        digitalWrite(EN_PIN, HIGH); //disable stepper
        isHomed = true;
        IsOpen = false;
      }
    } 
    
    else if ( human_d > D_THRESHOLD && !IsOpen )
    {
      //MOVE FORWARD
      digitalWrite(EN_PIN, LOW); //enable stepper
      isHomed = false; // homing management
      IsOpen = true;
      
      // Return to starting position (0mm)
      stepper.setMaxSpeed(FORW_SPEED);
      stepper.moveTo(D_OUT * STEP_PER_MM);
  
      // Disabling management
      if (stepper.currentPosition() == D_OUT)
      {
        digitalWrite(EN_PIN, HIGH); //disable stepper
      }
    }
  stepper.run(); // (non-blocking)
  }
}
