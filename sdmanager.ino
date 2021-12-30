#include <SPI.h>
//#include <SD.h>
#include "SdFat.h"
SdFat SD;

File myFile;
String filename;
String payload;
int packages;
int last;
byte buffer[201];
char terminator = 58;
char seminator = 33;
char awk[3] = "awk";


void setup() {
  Serial.begin(500000);
  while (!Serial) {
  }
//  Serial.print("Initializing SD card...");
  if (!SD.begin(10)) {
//    Serial.println("initialization failed!");
    while (1);
  }
//  Serial.println("initialization done.");
  Serial.setTimeout(10000);
  Serial.print("READY!");
}
void sendAwk() {
    Serial.print("awk");
}
void loop() {
  payload = Serial.readStringUntil(terminator);
  if (payload == "filename") {
    filename = Serial.readStringUntil(seminator);
    sendAwk();
  } else if (payload == "packages") {
    packages = Serial.readStringUntil(seminator).toInt();
    sendAwk();
  } else if (payload == "last") {
    last = Serial.readStringUntil(seminator).toInt();
    sendAwk();
  } else if (payload == "start") {
    SD.remove(filename);
    myFile = SD.open(filename, FILE_WRITE);
    sendAwk();
    for (int i = 1; i < packages; i++) {
      Serial.readBytes(buffer, 200);
      myFile.write(buffer, 200);
      myFile.flush();
      sendAwk();
    }
    Serial.readBytes(buffer, last);
    myFile.write(buffer, last);
    myFile.flush();
    sendAwk();
    myFile.close();
    delay(1000);
    Serial.print("DONE!");
  }
}
