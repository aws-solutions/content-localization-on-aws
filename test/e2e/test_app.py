######################################################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                    #
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

import pytest
from datetime import datetime
import time
import json
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By


@pytest.fixture
def browser():
    chrome_options = Options()
    
    ####### TESTING - remove headless to see browser actions
    # Make sure the window is large enough in headless mode so that all
    # the elements on the page are visible
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    ####### TESTING - remove headless to see browser actions
    from selenium import webdriver

    browser = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=chrome_options)
    yield browser
    browser.quit()

# Test the happy path through the Content Localization app by loading and verifying data after a successful workflow run.  No
# CRUD interactions such as creating vocabularies are included here
# This test assumes that the second workflow in the collection is the one created by the
# workflow_with_customizations fixture
def test_complete_app(browser, workflow_with_customizations, testing_env_variables):

    #### TESTING - workflow is already created
    # To run this test in an environment where the workflow is already created, 
    # set the environment variable USE_EXISTING_WORKFLOW=True
    # This option is extremely useful for debugging issues with the test
    #### TESTING - workflow is already created

    browser.implicitly_wait(5)
    browser.get(testing_env_variables['APP_ENDPOINT'])

    ####### Login

    username_field = browser.find_element_by_xpath("/html/body/div[1]/div/div/div/div[2]/div[1]/div/input")
    username_field.send_keys(testing_env_variables['APP_USERNAME'])
    password_field = browser.find_element_by_xpath("/html/body/div[1]/div/div/div/div[2]/div[2]/input")
    password_field.send_keys(testing_env_variables['APP_PASSWORD'])
    browser.find_element_by_xpath("/html/body/div[1]/div/div/div/div[3]/span[1]/button").click()
    
    time.sleep(60)
    
    # Verify log in is successful
    header_element = browser.find_element_by_xpath("/html/body/div/div/div[1]/div[2]/div[1]/h1")
    header = header_element.get_attribute("textContent")
    assert "Media Collection" in header

    # Verify log in is successful by checking the landing page is loaded
    header_element = browser.find_element_by_xpath("/html/body/div/div/div[1]/div[2]/div[1]/h1")
    header = header_element.get_attribute("textContent")
    assert "Media Collection" in header

    ####### UPLOAD VIEW
    # Visit all the input form elements that should be activated with the default workflow configuration
    # Do not run any workflows
    
    # Navigate to the Upload View
    
    #browser.find_element_by_link_text("Upload").click()
    browser.find_element_by_xpath("/html/body/div/div/div[1]/div[1]/nav/div/ul/li[1]/a").click()                            

    # Check the default boxes are set for the subtitles workflow

    # Expand the configure workflow menu
    browser.find_element_by_xpath("/html/body/div/div/div[2]/button[1]").click()
    time.sleep(5)
    # Configure transcribe
    transcribe_language_box = browser.find_element_by_xpath("/html/body/div/div/div[2]/div[2]/div/div[1]/div[2]/div[2]/fieldset/div/div/div[2]/select[1]")
    # # default source language selection should be set for auto detection
    assert transcribe_language_box.get_attribute("value") == "en-US"
    
    transcribe_language_box.send_keys("ru-RU")
    
    # # now it should be ru-RU
    assert transcribe_language_box.get_attribute("value") == "ru-RU"
    
     ####### Collection View
     # Navigate to Collection view
    #browser.find_element_by_link_text("Collection").click()
    browser.find_element_by_xpath("/html/body/div/div/div[1]/nav/div/ul/li[2]/a").click()
    time.sleep(5)

    # Find the base test asset in the collection
    # FIXME - it would be better to find the workflow with the correct assetId, but I can't figure out how to do it with selenium.  
    # Instead, we are taking the second workflow in the list and assume it is the one for the test

    ####### TRANSCRIPT COMPONENT
    # Navigate to the transcript
    #Analyze
    #browser.find_element_by_link_text("Analyze").click()
    browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div/div/div/div[1]/div/div/table/tbody/tr[2]/td[6]/a[1]").click()
    time.sleep(5)
    #Speech Recognition is the default tab
    #Transcript
    #browser.find_element_by_link_text("Transcript").click()
    browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[1]/div[1]/div/div/div[2]/div[1]/div/div[1]/ul/li[1]/a").click()
    time.sleep(8)

    # Check the text for some keywords from the test video
    transcript_text = browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[1]/div[2]/div/div").get_attribute("textContent")
    assert("farm to" in transcript_text)

    # Download text
    browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[1]/div[2]/div/div/button").click()
    
    # Check the video player
    player = browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[2]/div[1]/div/div[1]/div/video")
    # Play big button
    browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[2]/div[1]/div/div[1]/div/button").click()
   

    # Check the File Information
    duration = browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[2]/div[2]/div/div/div/div/div/div/div[1]/div[1]").get_attribute("textContent")
    # SHould look like: "Video duration:\n              00:09\n            "
    assert duration.split()[0] == "Video"
    assert len(duration.split()) == 3
    
    ####### SUBTITLES COMPONENT
    # Navigate to subtitles
    #browser.find_elements_by_link_text("Subtitles")[0].click()
    browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[1]/div[1]/div/div/div[2]/div[1]/div/div[1]/ul/li[2]/a").click()
    wait = WebDriverWait(browser, 120)
    wait.until(EC.presence_of_element_located((By.ID, "caption0")))

    # Check a subtitle
    subtitle1 = browser.find_element_by_xpath("/html/body/div[1]/div/div[2]/div/div[1]/div[2]/div/div/div/div/table/tbody/tr[1]/td[2]/div/div/div[1]/textarea")
    subtitle1_text = subtitle1.get_attribute("value")
    assert "Boulder" in subtitle1_text

    # Edit a subtitle
    time.sleep(1)
    file_name = f'{datetime.today().strftime("%Y-%m-%d_%H:%M")}.png'.replace("/","_").replace("::","__")
    browser.save_screenshot(file_name)
    subtitle1.send_keys("\ue003\ue003\ue003\ue003\ue003\ue003\ue003\ue003 00STEEN REPLACED BY EDITS00")

    # Check the file info
    source_language = browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[2]/div[2]/div/div/div/div/div/div/div[2]/div[3]").get_attribute("textContent")
    # Should look like: "Source Language: English, US"
    assert "English" in source_language

    # Test download button
    browser.find_element_by_xpath("/html/body/div[1]/div/div[2]/div/div[1]/div[2]/div/div/button[1]").click()
    
    # Test vocabularies
    # Save vocabulary button
    browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[1]/div[2]/div/div/button[2]").click()
    # Check the table for the edits
    vocabylary_1_display_as = browser.find_element_by_xpath("/html/body/div[3]/div[1]/div/div/div/div[3]/table/tbody/tr/td[5]/div/div[1]/div/input").get_attribute("value")
    assert "00STEEN REPLACED BY EDITS00" in vocabylary_1_display_as

    # Name vocabulary
    # Invalid name
    vocabulary_name_box = browser.find_element_by_xpath("/html/body/div[2]/div[1]/div/div/div/div[1]/div[2]/input")
    vocabulary_name_box.send_keys("automated_test_vocabulary")
    error_text = browser.find_element_by_xpath("/html/body/div[2]/div[1]/div/div/div/div[4]").get_attribute("textContent")
    assert "Invalid vocabulary name" in error_text
    vocabulary_name_box.clear()
    # valid name
    vocabulary_name_box.send_keys("automatedtestvocabulary")

    # Add a row to vocabulary
    time.sleep(1)
    browser.find_element_by_xpath("/html/body/div[2]/div[1]/div/div/div/div[3]/table/tbody/tr/td[5]/div/div[2]/span[2]/button").click()
    time.sleep(3)
    # Delete a row from vocabulary
    browser.find_element_by_xpath("/html/body/div[2]/div[1]/div/div/div/div[3]/table/tbody/tr[2]/td[5]/div/div[2]/span[1]/button").click()
    
    # Cancel 
    browser.find_element_by_xpath('/html/body/div[2]/div[1]/div/div/footer/button[1]').click()

    time.sleep(5)

     ####### TRANSLATE COMPONENT
     # Navigate to translation
    #browser.find_elements_by_link_text("Translation")[0].click()
    browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[1]/div[1]/div/div/div[2]/div[1]/div/div[1]/ul/li[3]/a").click()
    wait = WebDriverWait(browser, 120)
    wait.until(EC.presence_of_element_located((By.ID, "caption0")))

    # Check the radio button menus at the top - the language shoulf be Spanish
    button_language = browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[1]/div[2]/div/div/fieldset/div/div/div/label").get_attribute("textContent")
    assert button_language == "Spanish"

    # Check a subtitle
    subtitle1 = browser.find_element_by_xpath("/html/body/div[1]/div/div[2]/div/div[1]/div[2]/div/div/div/div/table/tbody/tr[1]/td[2]/div/div/div[1]/textarea")
    subtitle1_text = subtitle1.get_attribute("value")
    assert "Boulder" in subtitle1_text

    # Note that this test case had to change due to a change in an external service.
    # The subtitles that are generated are slightly different. The modified subtitle was previously
    # in table row 3 but now it is merged into the second subtitle so we find it in table row 2.
    subtitle3 = browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[1]/div[2]/div/div/div[1]/div/table/tbody/tr[2]/td[2]/div/div/div[1]/textarea")
    subtitle3_text = subtitle3.get_attribute("value")
    assert "JEFF STEEN-replaced-by-terminology" in subtitle3_text

    # Edit a subtitle
    # For a clean edit, we need to back up to a space and avoid breaking a word.
    # Originally we backspaced 12 times, which worked until it didn't. So, lets do at least 11
    # then find the first space before that and calculate the number of characters we need to strip
    # off the end to reach the space character.
    num_characters_to_backspace_over = len(subtitle1_text) - (subtitle1_text[0:-11].rfind(' ') + 1)
    subtitle1.send_keys(("\ue003" * num_characters_to_backspace_over) + "00terminology REPLACED BY EDITS00")

    # Check the file info
    time.sleep(2)
    source_language = browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[2]/div[2]/div/div/div/div/div/div/div[2]/div[3]").get_attribute("textContent")
    # Should look like: "Source Language: English, US"
    assert "English" in source_language

    # Test download buttons
    # VTT
    #browser.find_elements_by_link_text("Download VTT").click()
    browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[1]/div[2]/div/div/div[2]/ul/li[1]/a")
    #browser.find_elements_by_link_text("Download SRT").click()
    browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[1]/div[2]/div/div/div[2]/ul/li[2]/a")
    #browser.find_elements_by_link_text("Download Audio").click()
    browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[1]/div[2]/div/div/div[2]/ul/li[3]/a")
    
    # Test terminologies
    # Save Edits button
    browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[1]/div[2]/div/div/button[2]").click()
    # Save terminology button
    browser.find_element_by_xpath("/html/body/div/div/div[2]/div/div[1]/div[2]/div/div/button[1]").click()
    # Check the table for the edits
    vocabylary_1_display_as = browser.find_element_by_xpath("/html/body/div[2]/div[1]/div/div/div/div[4]/table/tbody/tr/td[2]/div/div/div[1]/div/input").get_attribute("value")
    assert vocabylary_1_display_as == "00terminology REPLACED BY EDITS00" 

    # Add language
    browser.find_element_by_xpath("/html/body/div[2]/div[1]/div/div/div/div[4]/table/caption/span/button[1]").click()
    # select hebrew
    browser.find_element_by_xpath("/html/body/div[3]/div[1]/div/div/div/select").send_keys("he")
    time.sleep(2)
    # save
    browser.find_element_by_xpath("/html/body/div[3]/div[1]/div/div/footer/button[2]").click()


    # Name terminology
    # Invalid name
    terminology_name_box = browser.find_element_by_xpath("/html/body/div[2]/div[1]/div/div/div/div[2]/input")
    terminology_name_box.send_keys("automated test terminology")
    error_text = browser.find_element_by_xpath("/html/body/div[2]/div[1]/div/div/div/div[5]").get_attribute("textContent")
    assert "Invalid terminology name" in error_text
    terminology_name_box.clear()
    # valid name
    terminology_name_box.send_keys("automatedtestterminology")

    # Add a row to terminology
    browser.find_element_by_xpath("/html/body/div[2]/div[1]/div/div/div/div[4]/table/tbody/tr/td[2]/div/div/div[2]/span[2]/button").click()
    # # Delete a row from terminology
    browser.find_element_by_xpath("/html/body/div[2]/div[1]/div/div/div/div[4]/table/tbody/tr[2]/td[2]/div/div/div[2]/span[1]/button").click()
    
    # Save terminology validation - terminolgy can't be saved becasue it has empty cells - alert element should exist
    browser.find_element_by_xpath("/html/body/div[2]/div[1]/div/div/div/div[5]")

    # Cancel 
    browser.find_element_by_xpath('/html/body/div[2]/div[1]/div/div/footer/button[1]').click()

    time.sleep(5)

    # Sign out
    browser.find_element_by_xpath("/html/body/div/div/div[1]/nav/div/ul/li[4]/a/p").click()
