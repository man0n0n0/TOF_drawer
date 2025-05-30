// Handle root page GET request
void handleRoot() {
  String html = "<!DOCTYPE html>"
    "<html>"
    "<head>"
    "    <title>ALINE BOUVY: Drawer Setup</title>"
    "    <meta charset=\"UTF-8\">"
    "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
    "    <style>"
    "        body {"
    "            font-family: Arial, sans-serif;"
    "            background-color: #f4f4f4;"
    "            margin: 0;"
    "            padding: 0;"
    "        }"
    "        .container {"
    "            max-width: 600px;"
    "            margin: 20px auto;"
    "            padding: 0 20px;"
    "        }"
    "        h1 {"
    "            text-align: center;"
    "            margin-bottom: 20px;"
    "        }"
    "        .message {"
    "            background-color: #d4edda;"
    "            border: 1px solid #c3e6cb;"
    "            color: #155724;"
    "            padding: 10px;"
    "            margin-bottom: 20px;"
    "            border-radius: 4px;"
    "            display: none;"
    "        }"
    "        form {"
    "            background-color: #fff;"
    "            padding: 20px;"
    "            border-radius: 8px;"
    "            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);"
    "        }"
    "        .form-group {"
    "            margin-bottom: 20px;"
    "        }"
    "        label {"
    "            display: block;"
    "            margin-bottom: 8px;"
    "            font-weight: bold;"
    "        }"
    "        .slider-container {"
    "            display: flex;"
    "            align-items: center;"
    "        }"
    "        input[type=\"range\"] {"
    "            flex: 1;"
    "            margin-right: 10px;"
    "        }"
    "        .value-display {"
    "            min-width: 60px;"
    "            text-align: right;"
    "            font-weight: bold;"
    "        }"
    "        .buttons {"
    "            display: flex;"
    "            justify-content: space-between;"
    "            margin-top: 20px;"
    "        }"
    "        button {"
    "            background-color: #000000;"
    "            color: #fff;"
    "            padding: 10px 15px;"
    "            border: none;"
    "            border-radius: 4px;"
    "            cursor: pointer;"
    "            font-size: 16px;"
    "        }"
    "        button:hover {"
    "            background-color: #333333;"
    "        }"
    "        .reset-btn {"
    "            background-color: #6c757d;"
    "        }"
    "        .reset-btn:hover {"
    "            background-color: #5a6268;"
    "        }"
    "    </style>"
    "</head>"
    "<body>"
    "    <div class=\"container\">"
    "        <h1>ALINE BOUVY: Drawer Variables</h1>"
    "        <p> modify variables needed and save settings. Reboot the drawer and changes should be operatives</p>"
    "        "
    "        <div id=\"message\" class=\"message\"></div>"
    "        "
    "        <form id=\"settingsForm\" action=\"/\" method=\"post\">"
    "            <div class=\"form-group\">"
    "                <label for=\"BACK_SPEED\">Retraction Speed (step/sec):</label>"
    "                <div class=\"slider-container\">"
    "                    <input type=\"range\" id=\"BACK_SPEED\" name=\"BACK_SPEED\" min=\"5000\" max=\"18000\" value=\"" + String(BACK_SPEED) + "\" oninput=\"updateSliderValue('BACK_SPEED', 'BACK_SPEEDValue')\">"
    "                    <span id=\"BACK_SPEEDValue\" class=\"value-display\">" + String(BACK_SPEED) + "</span>"
    "                </div>"
    "            </div>"
    "            "
    "            <div class=\"form-group\">"
    "                <label for=\"FORW_SPEED\">Exit Speed (step/sec):</label>"
    "                <div class=\"slider-container\">"
    "                    <input type=\"range\" id=\"FORW_SPEED\" name=\"FORW_SPEED\" min=\"500\" max=\"2000\" value=\"" + String(FORW_SPEED) + "\" oninput=\"updateSliderValue('FORW_SPEED', 'FORW_SPEEDValue')\">"
    "                    <span id=\"FORW_SPEEDValue\" class=\"value-display\">" + String(FORW_SPEED) + "</span>"
    "                </div>"
    "            </div>"
    "            "
    "            <div class=\"form-group\">"
    "                <label for=\"D_THRESHOLD\">Minimum Distance Threshold (cm):</label>"
    "                <div class=\"slider-container\">"
    "                    <input type=\"range\" id=\"D_THRESHOLD\" name=\"D_THRESHOLD\" min=\"50\" max=\"500\" value=\"" + String(D_THRESHOLD) + "\" oninput=\"updateSliderValue('D_THRESHOLD', 'D_THRESHOLDValue')\">"
    "                    <span id=\"D_THRESHOLDValue\" class=\"value-display\">" + String(D_THRESHOLD) + "</span>"
    "                </div>"
    "            </div>"
    ""
    "            <div class=\"form-group\">"
    "                <label for=\"WAIT_INSIDE\">Waiting time after retraction (ms):</label>"
    "                <div class=\"slider-container\">"
    "                    <input type=\"range\" id=\"WAIT_INSIDE\" name=\"WAIT_INSIDE\" min=\"1000\" max=\"10000\" value=\"" + String(WAIT_INSIDE) + "\" oninput=\"updateSliderValue('WAIT_INSIDE', 'WAIT_INSIDEValue')\">"
    "                    <span id=\"WAIT_INSIDEValue\" class=\"value-display\">" + String(WAIT_INSIDE) + "</span>"
    "                </div>"
    "            </div>"
    "            "
    "            <div class=\"buttons\">"
    "                <button type=\"submit\">Save Settings</button>"
    "                <button type=\"button\" onclick=\"resetForm()\" class=\"reset-btn\">Reset</button>"
    "            </div>"
    "        </form>"
    "    </div>"
    ""
    "    <script>"
    "        function updateSliderValue(sliderId, spanId) {"
    "            var slider = document.getElementById(sliderId);"
    "            var span = document.getElementById(spanId);"
    "            span.innerHTML = slider.value;"
    "        }"
    "        "
    "        function resetForm() {"
    "            document.getElementById('settingsForm').reset();"
    "            // Update all displayed values after reset"
    "            updateSliderValue('BACK_SPEED', 'BACK_SPEEDValue');"
    "            updateSliderValue('FORW_SPEED', 'FORW_SPEEDValue');"
    "            updateSliderValue('D_THRESHOLD', 'D_THRESHOLDValue');"
    "            updateSliderValue('WAIT_INSIDE', 'WAIT_INSIDEValue');"
    "        }"
    "        "
    "        function showMessage(message, isError = false) {"
    "            var messageElement = document.getElementById('message');"
    "            messageElement.textContent = message;"
    "            messageElement.style.display = 'block';"
    "            "
    "            if (isError) {"
    "                messageElement.style.backgroundColor = '#f8d7da';"
    "                messageElement.style.borderColor = '#f5c6cb';"
    "                messageElement.style.color = '#721c24';"
    "            } else {"
    "                messageElement.style.backgroundColor = '#d4edda';"
    "                messageElement.style.borderColor = '#c3e6cb';"
    "                messageElement.style.color = '#155724';"
    "            }"
    "            "
    "            // Hide message after 3 seconds"
    "            setTimeout(function() {"
    "                messageElement.style.display = 'none';"
    "            }, 3000);"
    "        }"
    "        "
    "        // Init all sliders' displayed values on page load"
    "        window.onload = function() {"
    "            updateSliderValue('BACK_SPEED', 'BACK_SPEEDValue');"
    "            updateSliderValue('FORW_SPEED', 'FORW_SPEEDValue');"
    "            updateSliderValue('D_THRESHOLD', 'D_THRESHOLDValue');"
    "            updateSliderValue('WAIT_INSIDE', 'WAIT_INSIDEValue');"
    "        };"
    "    </script>"
    "</body>"
    "</html>";
  
  server.send(200, "text/html", html);
}

// Handle form submission
void handleFormSubmission() {
  bool valuesChanged = false;
  
  if (server.hasArg("D_THRESHOLD")) {
    int newVal = server.arg("D_THRESHOLD").toInt();
    if (newVal != D_THRESHOLD) {
      D_THRESHOLD = newVal;
      valuesChanged = true;
    }
  }
  
  if (server.hasArg("BACK_SPEED")) {
    int newVal = server.arg("BACK_SPEED").toInt();
    if (newVal != BACK_SPEED) {
      BACK_SPEED = newVal;
      valuesChanged = true;
    }
  }
  
  if (server.hasArg("FORW_SPEED")) {
    int newVal = server.arg("FORW_SPEED").toInt();
    if (newVal != FORW_SPEED) {
      FORW_SPEED = newVal;
      valuesChanged = true;
    }
  }
  
  if (server.hasArg("WAIT_INSIDE")) {
    int newVal = server.arg("WAIT_INSIDE").toInt();
    if (newVal != WAIT_INSIDE) {
      WAIT_INSIDE = newVal;
      valuesChanged = true;
    }
  }
  
  // Save to storage if values changed
  if (valuesChanged) {
    saveValues();
  }
  
  // Redirect back to the root page
  server.sendHeader("Location", "/", true);
  server.send(302, "text/plain", "");
}
