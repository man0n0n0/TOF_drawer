// Load saved values from persistent storage
void loadSavedValues() {
  Serial.println("Loading saved values...");
  
  preferences.begin("drawer", false);
  
  // If the key exists, read it, otherwise keep the default value
  if (preferences.isKey("D_THRESHOLD")) {
    D_THRESHOLD = preferences.getInt("D_THRESHOLD", D_THRESHOLD);
  }
  
  if (preferences.isKey("BACK_SPEED")) {
    BACK_SPEED = preferences.getInt("BACK_SPEED", BACK_SPEED);
  }
  
  if (preferences.isKey("FORW_SPEED")) {
    FORW_SPEED = preferences.getInt("FORW_SPEED", FORW_SPEED);
  }
  
  if (preferences.isKey("WAIT_INSIDE")) {
    WAIT_INSIDE = preferences.getInt("WAIT_INSIDE", WAIT_INSIDE);
  }
  
  // Validate ranges
  if (D_THRESHOLD < 50 || D_THRESHOLD > 500) D_THRESHOLD = 100;
  if (BACK_SPEED < 5000 || BACK_SPEED > 18000) BACK_SPEED = 8000;
  if (FORW_SPEED < 500 || FORW_SPEED > 2000) FORW_SPEED = 1000;
  if (WAIT_INSIDE < 1000 || WAIT_INSIDE > 10000) WAIT_INSIDE = 3000;
  
  preferences.end();
  
  Serial.println("Current values:");
  Serial.println("D_THRESHOLD: " + String(D_THRESHOLD));
  Serial.println("BACK_SPEED: " + String(BACK_SPEED));
  Serial.println("FORW_SPEED: " + String(FORW_SPEED));
  Serial.println("WAIT_INSIDE: " + String(WAIT_INSIDE));
}

// Save values to persistent storage
void saveValues() {
  Serial.println("Saving values...");
  
  preferences.begin("drawer", false);
  
  preferences.putInt("D_THRESHOLD", D_THRESHOLD);
  preferences.putInt("BACK_SPEED", BACK_SPEED);
  preferences.putInt("FORW_SPEED", FORW_SPEED);
  preferences.putInt("WAIT_INSIDE", WAIT_INSIDE);
  
  preferences.end();
  
  Serial.println("Values saved.");
}
