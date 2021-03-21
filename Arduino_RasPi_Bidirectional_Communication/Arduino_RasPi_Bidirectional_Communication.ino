#include <Servo.h>
#include <SharpIR.h>
#define ir A0
#define model 1080
#define tiltPin 9
#define panPin 10 

Servo tiltServo;  
Servo panServo;
SharpIR SharpIR(ir, model);

int tiltAngle = 0;
int panAngle = 0;
int dis = 0;

const byte numChars = 64;
char tiltR[numChars];
char panR[numChars];
String tiltRS;
String panRS;
boolean newData = false;

byte ledPin = 13;   // the onboard LED

//===============

void setup() {
    Serial.begin(115200);
    tiltServo.attach(tiltPin);  
    panServo.attach(panPin); 
    pinMode(ledPin, OUTPUT);
    digitalWrite(ledPin, HIGH);
    delay(200);
    digitalWrite(ledPin, LOW);
    delay(200);
    digitalWrite(ledPin, HIGH);
    Serial.println("<Arduino is ready>");
}

//===============

void loop() {
    recvWithStartEndMarkers();
    replyToPython();
}
//===============

void recvWithStartEndMarkers() {
    static boolean recvInProgress = false;
    static boolean commaFound = false;
    static byte ndx = 0;
    char startMarker = '<';
    char endMarker = '>';
    char comma = ',';
    char rc;

    while (Serial.available() > 0 && newData == false) {
        rc = Serial.read();

        if (recvInProgress == true) {
            if (rc != endMarker) {
                if(rc != comma && !commaFound)
                  tiltR[ndx] = rc;
                else if(rc != comma && commaFound)
                  panR[ndx] = rc;
                if(rc == comma){
                  commaFound = true;
                  tiltR[ndx] = '\0';
                  ndx = 0;
                }
                else ndx++;
                if (ndx >= numChars) {
                    ndx = numChars - 1;
                }
            }else {
                panR[ndx] = '\0'; // terminate the string
                tiltRS = tiltR;
                tiltAngle = tiltRS.toInt();
                if(tiltAngle<0) tiltAngle = 0;
                if(tiltAngle>180) tiltAngle = 180;
                tiltServo.write(tiltAngle);  
                panRS = panR;               
                panAngle = panRS.toInt();
                if(panAngle<4) panAngle = 4;
                if(panAngle>140) panAngle = 140;
                panServo.write(panAngle);
                recvInProgress = false;
                commaFound= false;
                ndx = 0;
                newData = true;
                memset(panR, 0, sizeof(panR));
                memset(tiltR, 0, sizeof(tiltR));
            }
        }else if (rc == startMarker) {
            recvInProgress = true;
        }
        
    }
}

//===============

void replyToPython() {
    if (newData == true) {
      dis=SharpIR.distance();
      if(dis > 80) dis = 80;
      if(dis < 10 ) dis = 10;
      Serial.print('<');
      Serial.print(dis);
      Serial.print(',');
      Serial.print(tiltRS);
      Serial.print(',');
      Serial.print(panRS);
      Serial.print(',');
      Serial.print(millis());
      Serial.print('>');
      newData = false;
    }
}
