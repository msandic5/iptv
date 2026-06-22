#include <TFT_eSPI.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
//#include <Base64.h>
#include <WiFiClientSecure.h>
#include <IRremote.hpp>
#include "kodovi.h"

const char* ssid = "MSA";
const char* password = "S4nd1cm1";

// ntfy.sh topici — PROMIJENI ovo u svoja jedinstvena imena (služe kao lozinka!)
const char* ntfy_topic     = "klima-msandic-86";      // notifikacije iz ESP32 ka telefonu
const char* ntfy_cmd_topic = "klima-msandic-86-cmd";  // komande sa telefona ka ESP32

#define DHTPIN 5 //temp senzor prikljucen na pin 5
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

TFT_eSPI tft = TFT_eSPI();

#define IR_SEND_PIN 25


/*=====================================*/

// Šalje push notifikaciju preko ntfy.sh (bez registracije)
// Instaliraj ntfy aplikaciju na telefon i pretplati se na isti topic.
void sendNtfy(float temperature, float hum) {
  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  String ntfy_url = String("https://ntfy.sh/") + ntfy_topic;

  if (!http.begin(client, ntfy_url)) {
    Serial.println("[ntfy] http.begin neuspjesno");
    return;
  }

  http.addHeader("Title", "ESP32 KLIMA");
  http.addHeader("Tags", "thermometer,droplet");
  http.addHeader("Priority", "default");

  String body = "Temperatura: " + String(temperature, 1) + " C\n"
              + "Vlaznost:    " + String(hum, 1) + " %";

  int code = http.POST(body);
  if (code > 0) {
    Serial.printf("[ntfy] HTTP %d\n", code);
    Serial.println(http.getString());
  } else {
    Serial.printf("[ntfy] greska: %s\n", http.errorToString(code).c_str());
  }
  http.end();
}

/*=====================================*/

// Cita zadnju komandu sa ntfy.sh komandnog topica.
// Vraca prazan string ako nema novih poruka u zadnjih 10s.
String fetchNtfyCommand() {
  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  String url = String("https://ntfy.sh/") + ntfy_cmd_topic + "/json?poll=1&since=10s";

  if (!http.begin(client, url)) {
    Serial.println("[ntfy] fetch http.begin neuspjesno");
    return "";
  }

  String result = "";
  int code = http.GET();
  if (code == 200) {
    String body = http.getString();
    // NDJSON: jedna poruka po liniji. Uzimamo posljednju "message" event.
    int start = 0;
    while (start < (int)body.length()) {
      int end = body.indexOf('\n', start);
      if (end < 0) end = body.length();
      String line = body.substring(start, end);
      if (line.indexOf("\"event\":\"message\"") >= 0) {
        int msgIdx = line.indexOf("\"message\":\"");
        if (msgIdx >= 0) {
          msgIdx += 11; // duzina od \"message\":\"
          int msgEnd = line.indexOf("\"", msgIdx);
          if (msgEnd >= 0) {
            result = line.substring(msgIdx, msgEnd);
          }
        }
      }
      start = end + 1;
    }
  } else {
    Serial.printf("[ntfy] fetch HTTP %d\n", code);
  }
  http.end();
  return result;
}

/*=====================================*/

void setup() {
  /*IR*/
  IrSender.begin(IR_SEND_PIN); 
  /*temp*/
  dht.begin();
  /*serial*/
  Serial.begin(115200);
  /*display*/
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);  

  // Povezivanje na Wi-Fi mrežu
  tft.setTextSize(2);
  tft.setCursor(0, 0);
  WiFi.begin(ssid, password);
  tft.printf("Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    tft.printf(".");
  }
  tft.printf("Povezano!\r\n");
}

String last_command = "INIT";
void loop() {
    /*temp*/
    float temp = dht.readTemperature();
    float hum = dht.readHumidity();
    if (isnan(temp) || isnan(hum)) Serial.println("Greska: DHT22");
    tft.setTextSize(4);
    tft.setCursor(0, 20);
    tft.setTextColor(TFT_GREEN, TFT_BLACK);  
    tft.printf("Temp:%.1f\r\n", temp);
    tft.setTextSize(2);
    tft.setTextColor(TFT_RED, TFT_BLACK); 
    tft.println();
    tft.printf("Vlaznost:%.1f %%\r\n", hum);
    tft.println();
    tft.setTextColor(TFT_BLUE, TFT_BLACK);  
    tft.println("Poslednja komanda:");
    
    // Preuzimanje komande sa ntfy.sh
    String payload = fetchNtfyCommand();

    if (payload.length() == 0) {
      // nema novih poruka — samo prikaži zadnju komandu
      tft.printf(last_command.c_str());
    }
    else if (last_command == payload) {
      tft.printf(payload.c_str());
    }
    else {
      Serial.print("Nova komanda: "); Serial.println(payload);
      if (payload.startsWith("GET")) sendNtfy(temp, hum);
      if (payload.startsWith("ON20")) IrSender.sendRaw(COOL20, 200, 38);
      if (payload.startsWith("ON21")) IrSender.sendRaw(COOL21, 200, 38);
      if (payload.startsWith("ON22")) IrSender.sendRaw(COOL22, 200, 38);
      if (payload.startsWith("ON23")) IrSender.sendRaw(COOL23, 200, 38);
      if (payload.startsWith("ON24")) IrSender.sendRaw(COOL24, 200, 38);
      if (payload.startsWith("ON25")) IrSender.sendRaw(COOL25, 200, 38);
      if (payload.startsWith("OFF")) IrSender.sendRaw(OFF, 200, 38);
      if (payload.startsWith("SWING")) IrSender.sendRaw(SWING, 200, 38);
      last_command = payload;
      tft.printf(payload.c_str());
    }

    delay(5000);
    tft.fillRect(0, 30, 240, 105, TFT_BLACK); // Clear previous value

}