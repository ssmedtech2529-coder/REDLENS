# REDLENS
AI Non-Inversive Anemia Detection Method🩸
# Red Lens --- AI-Based Non-Invasive Anemia Screening Prototype

**Project type:** Biomedical engineering / AI screening prototype\
**Project ID:** BB-DM-01\
**Purpose:** Explore whether camera-based colour analysis and optical
sensor signals can support early anemia screening.

> **Important medical note:** This is a research and educational
> prototype, not a validated medical device. A camera, OpenCV, MAX30102,
> or other consumer optical sensor cannot by itself confirm hemoglobin
> level or diagnose anemia. Results must not replace a laboratory
> hemoglobin test or advice from a qualified healthcare professional.

## 1. Project Overview

Red Lens is a prototype that brings together:

-   **Image analysis:** OpenCV examines selected regions of an image,
    such as the nail bed and the inner lower eyelid (conjunctiva).
-   **Optical sensor input:** A connected sensor module may provide
    optical signals and related measurements. If the prototype displays
    an Hb estimate, it must be clearly labelled as an **experimental
    estimate**, not a direct laboratory measurement.
-   **Result comparison:** The app compares image-derived indicators
    with the sensor reading and shows whether the signals agree,
    disagree, or need to be retaken.
-   **History and reports:** The app may save screening sessions locally
    and create a summary report.

## 2. Problem Statement

Anemia can go undetected when people have limited access to screening
services. The project explores a low-cost, easy-to-use prototype that
could support preliminary screening in community settings, including
Anganwadi environments. It is not intended to replace clinical testing.

## 3. Project Objectives

1.  Capture images of the nail bed and inner lower eyelid.
2.  Use OpenCV to extract colour features from selected image regions.
3.  Read available data from a connected prototype sensor.
4.  Display a clear screening summary with limitations and next steps.
5.  Keep a local history of demo or research sessions.
6.  Evaluate the prototype against laboratory hemoglobin results before
    making any clinical claims.

## 4. Proposed System Workflow

1.  Enter a participant code or permitted basic details.
2.  Capture or upload a clear nail-bed image.
3.  Capture or upload a clear inner lower-eyelid image, when appropriate
    and safe.
4.  Check image quality and select the region of interest (ROI).
5.  Extract colour features using OpenCV.
6.  Read the connected sensor value, if available.
7.  Compare the image indicators and sensor data.
8.  Display one of the following:
    -   **Retake image:** image quality is insufficient.
    -   **Signals disagree:** the inputs do not match; do not provide a
        confident result.
    -   **Research screening indication:** experimental inputs suggest
        follow-up may be appropriate.
    -   **No clear indication from prototype:** this does not rule out
        anemia.
9.  Recommend clinical assessment and a laboratory hemoglobin test when
    needed.

## 5. Hardware Components

  -----------------------------------------------------------------------
  Component               Proposed role           Important limitation
  ----------------------- ----------------------- -----------------------
  ESP32 development board Reads supported sensors Needs suitable firmware
                          and sends data to the   and communication setup
                          app                     

  MAX30102 optical sensor Captures red/infrared   It does **not directly
  (optional)              photoplethysmography    measure hemoglobin**
                          signals; commonly used  
                          for pulse-related       
                          measurements            

  Finger clip or sensor   Helps maintain stable   Must be comfortable,
  holder                  sensor placement        clean, and consistently
                                                  positioned

  Camera or smartphone    Captures nail-bed and   Lighting, focus,
                          eye-region images       reflections, and camera
                                                  differences affect
                                                  colour

  OLED display (optional) Shows device status or  Displayed values are
                          raw prototype readings  not automatically
                                                  clinically valid

  USB power supply /      Powers the prototype    Follow electrical and
  battery                                         battery safety
                                                  practices
  -----------------------------------------------------------------------

**Do not describe an ordinary MAX30102 reading as a measured Hb value.**
Any experimental Hb estimate requires a clearly documented method,
calibration, and validation against laboratory results.

## 6. Software and Technologies

-   HTML --- page structure
-   CSS --- layout and visual design
-   JavaScript --- application logic
-   OpenCV.js --- image processing in the browser
-   ESP32 firmware --- sensor acquisition, if hardware is connected
-   Web Serial, Web Bluetooth, or a backend API --- optional
    communication route, depending on browser and hardware support
-   `localStorage` --- optional local demo history and calibration
    settings

## 7. Image Processing Concept

A research workflow may include:

1.  Load the image and check resolution, focus, and exposure.
2.  Select the nail-bed or conjunctiva region of interest.
3.  Reject images with excessive glare, blur, shadows, or incorrect
    framing.
4.  Convert the selected region into colour spaces such as RGB, HSV, or
    CIELAB.
5.  Calculate documented colour features, such as channel averages and
    colour ratios.
6.  Store features with the image-quality status and capture conditions.
7.  Compare results only with a model that has been trained and
    independently validated on suitable data.

**Colour features are not a diagnosis.** Skin tone, lighting, camera
processing, nail polish, eye conditions, and other factors can change
the image. Eye-region capture should be optional, respectful, and
performed only with appropriate consent and safe handling.

## 8. Sensor Data and Calibration

If a research model estimates hemoglobin:

-   Label the output **"Experimental Hb estimate"**.
-   Record the sensor model, firmware version, signal quality, and
    measurement conditions.
-   Collect paired prototype readings and laboratory hemoglobin results
    under an approved study protocol.
-   Use enough participants and a suitably diverse dataset; five samples
    are not enough to establish clinical validity.
-   Separate training, calibration, and independent test data by
    participant to avoid data leakage.
-   Report error measures and uncertainty, not just accuracy.
-   Obtain appropriate ethics approval, informed consent, and expert
    oversight for human-participant studies.
-   Do not use the prototype result to make treatment decisions.

A calibration curve alone does not make a device medically reliable.
Clinical validation is required before real-world screening claims.

## 9. Suggested Result Screen

Show these fields clearly:

-   Participant code (avoid unnecessary personal information)
-   Date and time
-   Nail image quality
-   Eye image quality, if used
-   OpenCV features / model output
-   Sensor type and raw signal quality
-   Experimental estimate, only if a documented model provides one
-   Agreement status between input methods
-   Recommended next step
-   Disclaimer: **"Prototype screening only --- not a diagnosis. Confirm
    with a laboratory hemoglobin test and a qualified healthcare
    professional."**

Do not display invented measurements as if they came from real hardware.
Mark simulated values as **DEMO DATA**.

## 10. Safety, Privacy, and Limitations

-   Obtain informed consent before capturing or storing images.
-   Collect only the information needed for the project.
-   Explain where data is stored and provide a way to clear demo
    records.
-   Do not upload identifiable images to an external AI service without
    clear consent and appropriate safeguards.
-   Do not use the prototype to rule out anemia, prescribe iron, or
    delay medical care.
-   Seek professional assessment for concerning symptoms; urgent
    symptoms such as chest pain, fainting, or severe breathing
    difficulty need prompt medical attention.
-   Validate performance across different skin tones, ages, lighting
    conditions, and relevant clinical groups.

## 11. Testing Plan

1.  **UI test:** Check that all buttons, forms, and report sections
    work.
2.  **Image test:** Test clear, blurry, dark, bright, and reflective
    images.
3.  **ROI test:** Confirm that the selected region matches the intended
    nail bed or conjunctiva.
4.  **Sensor test:** Verify the wiring, communication, and raw signal
    quality using known test procedures.
5.  **Failure test:** Ensure disconnected hardware or missing images
    produce a clear error rather than a fabricated result.
6.  **Repeatability test:** Repeat captures under controlled conditions
    and measure variation.
7.  **Research validation:** Compare the prototype with laboratory
    hemoglobin results under an approved protocol before claiming
    clinical performance.

## 12. Installation and Running

### Front-end demo

1.  Open the project folder in Visual Studio Code.
2.  Check that the HTML, CSS, and JavaScript files are in the expected
    locations.
3.  Run the page using a local development server, such as the VS Code
    Live Server extension, if the project needs one.
4.  Connect to the internet only if the app loads OpenCV.js or other
    libraries from a CDN.
5.  Allow camera access only when the browser asks and only if you
    intend to use the camera feature.
6.  Test with clearly labelled demo data before connecting hardware.

### Hardware connection

1.  Check the exact sensor pinout and voltage requirements from the
    component documentation.
2.  Connect the sensor to the ESP32 according to the circuit diagram for
    your specific board.
3.  Upload the matching firmware.
4.  Verify serial output and signal quality before connecting the web
    application.
5.  Never assume that the browser is receiving live hardware data unless
    the app confirms a successful connection.

Actual setup steps may differ depending on the files and hardware
included in your project.

## 13. Example Folder Structure

``` text
red-lens/
├── index.html
├── style.css
├── script.js
├── README.md
├── assets/
│   └── logo.png
├── firmware/
│   └── esp32_sensor.ino
└── reports/
```

This is a suggested structure; adjust it to match the existing project.

## 14. Future Improvements

-   Better image-quality checks and guided capture
-   Reliable ESP32 connection and clear connection status
-   Secure export of screening summaries
-   Improved dataset quality and independent validation
-   Accessibility and multilingual support
-   Evaluation with healthcare professionals and community stakeholders

## 15. Conclusion

Red Lens is an educational research prototype combining OpenCV-based
image analysis with optional optical-sensor data. Its purpose is to
explore a possible screening workflow, not to diagnose anemia.
Laboratory hemoglobin testing and professional clinical assessment
remain essential for confirmation.

## 16. Project Disclaimer

**Red Lens is a prototype for educational and research use only. It is
not a certified medical device and must not be used to diagnose, treat,
or rule out anemia. Any result must be confirmed through appropriate
laboratory testing and professional medical assessment.**
