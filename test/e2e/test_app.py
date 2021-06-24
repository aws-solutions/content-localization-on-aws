import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options


@pytest.fixture
def browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    browser = webdriver.Chrome(chrome_options=chrome_options)
    return browser

def test_complete_app(browser, testing_env_variables):
    browser.implicitly_wait(5)
    browser.get(testing_env_variables['APP_ENDPOINT'])

    ####### Login

    username_field = browser.find_element_by_xpath("/html/body/div[1]/div/div/div/div[2]/div[1]/div/input")
    username_field.send_keys(testing_env_variables['APP_USERNAME'])
    password_field = browser.find_element_by_xpath("/html/body/div[1]/div/div/div/div[2]/div[2]/input")
    password_field.send_keys(testing_env_variables['APP_PASSWORD'])
    browser.find_element_by_xpath("/html/body/div[1]/div/div/div/div[3]/span[1]/button").click()
    
    time.sleep(5)

    ####### Upload View
    # This test visits all the input form elements that should be activated with the default workflow configuration
    # It does not run any workflows
    
    # Navigate to the Upload View
    browser.find_element_by_xpath("/html/body/div[1]/div/div[1]/div[1]/nav/div/ul/li[1]/a").click()

    # Check the default boxes are set for the subtitles workflow

    # Expand the configure workflow menu
    browser.find_element_by_xpath("/html/body/div[1]/div/div[2]/div[2]/div/div/button[1]").click()
    # Configure transcribe
    transcribe_language_box = browser.find_element_by_xpath("/html/body/div[1]/div/div[2]/div[3]/div/div[1]/div[2]/div[2]/fieldset/div/div/div[2]/select[1]")
    
    # default language is en-US
    assert transcribe_language_box.get_attribute("value") == "en-US"
    
    transcribe_language_box.send_keys("ru-RU")
    #print(transcribe_language_box.value)
    print(dir(transcribe_language_box))
    
    # print(transcribe_language_box.tag_name)
    # print(transcribe_language_box.text)
    # now it should be ru-RU
    assert transcribe_language_box.get_attribute("value") == "ru-RU"
    
    # Configure subtitles
    subtitles_box = browser.find_element_by_xpath("/html/body/div[1]/div/div[2]/div[3]/div/div[1]/div[2]/div[2]/fieldset/div/div/div[4]/input")
    subtitles_box.send_keys("test.vtt")
    assert subtitles_box.get_attribute("value") == "test.vtt"

    # Configure translate language to en-ES
    
    translate_box = browser.find_element_by_xpath("/html/body/div[1]/div/div[2]/div[3]/div/div[1]/div[3]/div[2]/fieldset/div/div[3]/fieldset/div/div[2]/div[1]/p/input")
    assert translate_box.get_attribute("textContent") == ""
    # Select spanish badge
    browser.find_element_by_xpath("/html/body/div/div/div[2]/div[3]/div/div[1]/div[3]/div[2]/fieldset/div/div[3]/fieldset/div/div/div[2]/p/span[44]").click()
    
    # Check that spanish badge is in the input box
    assert browser.find_element_by_xpath("/html/body/div[1]/div/div[2]/div[3]/div/div[1]/div[3]/div[2]/fieldset/div/div[3]/fieldset/div/div/div[1]/span/span").get_attribute("textContent") == "Spanish"

    # click the Swedish badge
    browser.find_element_by_xpath("/html/body/div[1]/div/div[2]/div[3]/div/div[1]/div[3]/div[2]/fieldset/div/div[3]/fieldset/div/div/div[2]/p/span[45]").click()
    assert browser.find_element_by_xpath("/html/body/div[1]/div/div[2]/div[3]/div/div[1]/div[3]/div[2]/fieldset/div/div[3]/fieldset/div/div/div[1]/span[2]/span").get_attribute("textContent") == "Swedish"
    

    # Sign out
    browser.find_element_by_xpath("/html/body/div/div/div[1]/nav/div/ul/li[4]/a/p").click()