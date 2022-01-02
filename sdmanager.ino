#include <SPI.h>
//#include <SD.h>
#include "SdFat.h"
#define SD_FAT_TYPE 1
//SdFat SD;
SdFat32 SD;
File32 root;
File32 entry;

File myFile;
//File root;
//File entry;
String filename;
String payload;
String pwd;
int packages;
int last;
byte buffer[201];
char terminator = 58;
char seminator = 33;
const char awk[3] = "awk";
const char eoc[4] = "!eoc";  // end of command
const char eoi[4] = "!eoi";  // end of item

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
  } else if (payload == "navigate") {
    pwd = Serial.readStringUntil(seminator);
    root = SD.open(pwd);
    root.rewindDirectory();
    sendAwk();
    while (entry.openNext(&root, O_RDONLY)) {
      entry.printFileSize(&Serial);
      Serial.write(seminator);
      entry.printModifyDateTime(&Serial);
      Serial.write(seminator);
      entry.printName(&Serial);
      if (entry.isDir()) {
        Serial.write("!directory");
      } else {
        Serial.write("!file");
      }
      Serial.write(eoi);
      entry.close();
    }    
    Serial.print(eoc);
    root.close();
  } else if (payload == "delete") {
    pwd = Serial.readStringUntil(seminator);
    SD.remove(pwd);
  }
}
