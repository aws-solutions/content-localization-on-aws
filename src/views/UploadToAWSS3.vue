<template>
  <div>
    <Header :is-upload-active="true" />
    <br>
    <b-container>
      <div v-if="hasAssetParam">
        <a>Running analysis on existing asset: {{ assetIdParam }}</a>
      </div>
      <div v-else>
        <b-alert
          :show="dismissCountDown"
          dismissible
          variant="danger"
          @dismissed="dismissCountDown=0"
          @dismiss-count-down="countDownChanged"
        >
          {{ uploadErrorMessage }}
        </b-alert>
        <b-alert
          :show="showInvalidFile"
          variant="danger"
        >
          {{ invalidFileMessages[invalidFileMessages.length-1] }}
        </b-alert>
        <h1>Upload Content</h1>
        <b-form-file
          v-model="file"
          size="lg"
          placeholder="Choose a file or drop it here..."
          drop-placeholder="Drop file here..."
        >
        </b-form-file>
      </div>
      <br />
      <b-container v-if="isUploading">
        <b-progress :value="uploadValue" show-progress animated></b-progress>
      </b-container>
      <p>{{ description }}</p>
      <b-container>
        <b-row v-if="hasAssetParam">
          <b-col>
            <b-button v-b-toggle.collapse-2 class="m-1">
              Configure Workflow
            </b-button>
            <b-button v-if="validForm" variant="primary" @click="runWorkflow">
              Start Workflow
            </b-button>
            <b-button v-else disabled variant="primary">
              Start Workflow
            </b-button>
          </b-col>
        </b-row>
        <b-row v-else>
          <b-col>
            <b-button v-b-toggle.collapse-2 class="m-1">
              Configure Workflow
            </b-button>
            <b-button
              v-if="validForm"
              variant="primary"
              @click="uploadFiles"
            >
              Start Workflow
            </b-button>
            <b-button v-else disabled variant="primary">
              Start Workflow
            </b-button>
          </b-col>
        </b-row>
      </b-container>
      <br />
      <b-collapse id="collapse-2">
        <b-container class="text-left">
          <b-card-group deck>
            <b-card header="Video and Image Operators">
              <b-form-group>
                <b-form-checkbox-group
                  id="checkbox-group-1"
                  v-model="enabledOperators"
                  :options="videoOperators"
                  name="flavour-1"
                ></b-form-checkbox-group>
                <label>Thumbnail position:</label>
                <b-form-input v-model="thumbnail_position" type="range" min="1" max="20" step="1"></b-form-input>
                {{ thumbnail_position }} sec
                <b-form-input
                  v-if="enabledOperators.includes('faceSearch')"
                  id="Enter face collection id"
                  v-model="faceCollectionId"
                ></b-form-input>

                <b-form-input
                  v-if="enabledOperators.includes('genericDataLookup')"
                  v-model="genericDataFilename"
                  placeholder="Enter data filename"
                ></b-form-input>
              </b-form-group>
              <div v-if="videoFormError" style="color:red">
                {{ videoFormError }}
              </div>
            </b-card>
            <b-card header="Audio Operators">
              <b-form-group>
                <!--<b-form-checkbox-group-->
                <!--    id="checkbox-group-2"-->
                <!--    v-model="enabledOperators"-->
                <!--    :options="audioOperators"-->
                <!--    name="audioOperators"-->
                <!--&gt;-->
                <!--</b-form-checkbox-group>-->
                <b-form-checkbox-group id="checkbox-group-2" v-model="enabledOperators" name="audioOperators">
                  <b-form-checkbox value="Transcribe">
                    Transcribe
                  </b-form-checkbox>
                  <div v-if="enabledOperators.includes('Transcribe')">
                    Source Language
                    <b-form-select v-model="transcribeLanguage" :options="transcribeLanguages"></b-form-select>
                    <!--                  <b-form-checkbox-->
                    <!--                      id="enable_caption_editing"-->
                    <!--                      v-model="enable_caption_editing"-->
                    <!--                  >Pause workflow to edit captions before downstream processing</b-form-checkbox>-->
                    <br>
                    Custom Vocabulary
                    <b-form-select
                      v-model="customVocab"
                      :options="customVocabularyList"
                      text-field="name_and_status"
                      value-field="name"
                      disabled-field="notEnabled"
                    >
                      <template v-slot:first>
                        <b-form-select-option :value="null" disabled>
                          (optional)
                        </b-form-select-option>
                      </template>
                    </b-form-select>
                    <br>
                  </div>
                  <b-form-checkbox value="Subtitles">
                    Subtitles
                  </b-form-checkbox>
                  <div v-if="enabledOperators.includes('Subtitles')">
                    Use Existing Subtitles
                    <b-form-input v-model="existingSubtitlesFilename" placeholder="(optional) Enter .vtt filename"></b-form-input>
                  </div>
                </b-form-checkbox-group>
              </b-form-group>
              <div v-if="audioFormError" style="color:red">
                {{ audioFormError }}
              </div>
            </b-card>
            <b-card header="Text Operators">
              <b-form-group>
                <b-form-checkbox-group
                  id="checkbox-group-3"
                  v-model="enabledOperators"
                  :options="textOperators"
                  name="flavour-3"
                ></b-form-checkbox-group>
                <div v-if="enabledOperators.includes('Translate')" >
                   <!-- && customTerminologyList.length > 0"> -->
                   <!-- && customTerminologyList.filter(x => x.SourceLanguageCode === sourceLanguageCode).length > 0"> -->
                  <div v-if="customTerminology.length > 0"><b>Custom Terminologies:</b> ({{ customTerminology.length }} selected)</div>
                  <div v-else><b>Custom Terminologies:</b> ({{ customTerminology.length }} selected)</div>
                  <b-form-select
                    v-model="customTerminology"
                    :options="customTerminologyList.filter(x => x.SourceLanguageCode === sourceLanguageCode).map( x => { return {'text': x.Name + ' (' + x.TargetLanguageCodes + ')'  , 'value': {'Name': x.Name, 'TargetLanguageCodes': x.TargetLanguageCodes}}})"
                    multiple
                  >
                  </b-form-select>
                  <div v-if="overlappingTerminologies.length > 0" style="color:red">
                    You must not select terminologies that define translations for the same language. The following terminologies overlap:
                    <ul id="overlapping_terminologies">
                      <li v-for="terminology in overlappingTerminologies">
                        {{ terminology }}
                      </li>
                    </ul>
                  </div>
                  <div v-if="parallelDataList.length > 0"><b>Parallel Data:</b> ({{ parallelData.length }} selected) </div>
                  <div v-else><b>Parallel Data:</b></div>
                  <b-form-select
                    v-model="parallelData"
                    :options="parallelDataList.filter(x => x.SourceLanguageCode === sourceLanguageCode).map( x => { return {'text': x.Name + ' (' + x.TargetLanguageCodes + ')'  , 'value': {'Name': x.Name, 'TargetLanguageCodes': x.TargetLanguageCodes}}})"
                    multiple
                  >
                  </b-form-select>
                  <div v-if="overlappingParallelData.length > 0" style="color:red">
                    You must not select Parallel Data that define translations for the same language. The following Parallel Data overlap:
                    <ul id="overlapping_parallel_data">
                      <li v-for="parallel_data in overlappingParallelData">
                        {{ parallel_data }}
                      </li>
                    </ul>
                  </div>
                </div>
                <div v-if="enabledOperators.includes('Translate')" >
                  <b-form-group>
                    <b>Target Languages:</b>
                    <div v-if="textFormError" style="color:red">
                      {{ textFormError }}
                    </div>
                    <voerro-tags-input
                      v-model="selectedTranslateLanguages"
                      element-id="target_language_tags"
                      :limit="10"
                      :hide-input-on-limit="true"
                      :existing-tags="translateLanguageTags"
                      :only-existing-tags="true"
                      :add-tags-on-space="true"
                      :add-tags-on-comma="true"
                      :add-tags-on-blur="true"
                      :sort-search-results="true"
                      :typeahead-always-show="true"
                      :typeahead-hide-discard="true"
                      :typeahead="true"
                    />
                  </b-form-group>
                </div>
              </b-form-group>
            </b-card>
          </b-card-group>
          <div align="right">
            <button type="button" class="btn btn-link" @click="selectAll">
              Select All
            </button>
            <button type="button" class="btn btn-link" @click="clearAll">
              Clear All
            </button>
          </div>
        </b-container>
      </b-collapse>
    </b-container>
    <b-container v-if="executed_assets.length > 0">
      <label>
        Execution History
      </label>
      <b-table
        :fields="fields"
        bordered
        hover
        small
        responsive
        show-empty
        fixed
        :items="executed_assets"
      >
        <template v-slot:cell(workflow_status)="data">
          <a v-if="data.item.workflow_status !== 'Queued'"
            href
            @click.stop.prevent="openWindow(data.item.state_machine_console_link)"
          >{{ data.item.workflow_status }}</a>
          <div v-if="data.item.workflow_status === 'Queued'">{{ data.item.workflow_status }}</div>
        </template>
      </b-table>
      <b-button size="sm" @click="clearHistory">
        Clear History
      </b-button>
    </b-container>
  </div>
</template>

<script>
import Header from "@/components/Header.vue"
import VoerroTagsInput from "@/components/VoerroTagsInput.vue";
import "@/components/VoerroTagsInput.css";

import { mapState } from "vuex"

export default {
  components: {
    Header,
    VoerroTagsInput
  },
  data() {
    return {
      file: null,
      isUploading: null,
      uploadValue: null,
      customVocabularyList: [],
      selectedTags: [
      ],
      show_disclaimer: true,
      create_video_stream: true,
      valid_media_types: [
        "cmaf",
        "dash",
        "hls",
        "mp4",
        "f4v",
        "mxf",
        "mov",
        "ismv",
        "raw",
        "av1",
        "avc",
        "hevc",
        "mpeg-2",
        "avi",
        "mkv",
        "webm"
      ], // see https://docs.aws.amazon.com/mediaconvert/latest/ug/reference-codecs-containers.html
      fields: [
        {
          asset_id: {
            label: "Asset Id",
            sortable: false
          }
        },
        {
          file_name: {
            label: "File Name",
            sortable: false
          }
        },
        {
          workflow_status: {
            label: "Workflow Status",
            sortable: false
          }
        }
      ],
      thumbnail_position: 10,
      hasAssetParam: false,
      assetIdParam: "",
      upload_in_progress: false,
      enabledOperators: [
        "thumbnail", 
        "Transcribe", 
        "Translate", 
        "Subtitles"
      ],
      enable_caption_editing: false,
      videoOperators: [
        { text: "Object Detection", value: "labelDetection" },
        { text: "Celebrity Recognition", value: "celebrityRecognition" },
        { text: "Content Moderation", value: "contentModeration" },
        { text: "Face Detection", value: "faceDetection" },
        { text: "Word Detection", value: "textDetection" },
        { text: "Face Search", value: "faceSearch" },
        { text: "Generic Data Lookup (video only)", value: "genericDataLookup" }
      ],
      audioOperators: [
        { text: "Transcribe", value: "Transcribe" },
        {text: "Subtitles", value: "Subtitles"}
      ],
      textOperators: [
        { text: "Comprehend Key Phrases", value: "ComprehendKeyPhrases" },
        { text: "Comprehend Entities", value: "ComprehendEntities" },
        { text: "Translate", value: "Translate" }
      ],
      faceCollectionId: "",
      genericDataFilename: "",
      customVocab: null,
      customTerminology: [],
      customTerminologyList: [],
      parallelData: [],
      parallelDataList: [],
      existingSubtitlesFilename: "",
      transcribeLanguage: "en-US",
      transcribeLanguages: [
        { text: "Arabic, Gulf", value: "ar-AE" },
        { text: "Arabic, Modern Standard", value: "ar-SA" },
        { text: "Chinese Mandarin", value: "zh-CN" },
        { text: "Dutch", value: "nl-NL" },
        { text: "English, Australian", value: "en-AU" },
        { text: "English, British", value: "en-GB" },
        { text: "English, Indian-accented", value: "en-IN" },
        { text: "English, Irish", value: "en-IE" },
        { text: "English, Scottish", value: "en-AB" },
        { text: "English, US", value: "en-US" },
        { text: "English, Welsh", value: "en-WL" },
        // Disabled until 'fa' supported by AWS Translate
        // {text: 'Farsi', value: 'fa-IR'},
        { text: "French", value: "fr-FR" },
        { text: "French, Canadian", value: "fr-CA" },
        { text: "German", value: "de-DE" },
        { text: "German, Swiss", value: "de-CH" },
        { text: "Hebrew", value: "he-IL" },
        { text: "Hindi", value: "hi-IN" },
        { text: "Indonesian", value: "id-ID" },
        { text: "Italian", value: "it-IT" },
        { text: "Japanese", value: "ja-JP" },
        { text: "Korean", value: "ko-KR" },
        { text: "Malay", value: "ms-MY" },
        { text: "Portuguese", value: "pt-PT" },
        { text: "Portuguese, Brazilian", value: "pt-BR" },
        { text: "Russian", value: "ru-RU" },
        { text: "Spanish", value: "es-ES" },
        { text: "Spanish, US", value: "es-US" },
        { text: "Tamil", value: "ta-IN" },
        // Disabled until 'te' supported by AWS Translate
        // {text: 'Telugu', value: 'te-IN'},
        { text: "Turkish", value: "tr-TR" }
      ],
      translateLanguages: [
        { text: "Afrikaans", value: "af" },
        { text: "Albanian", value: "sq" },
        { text: "Amharic", value: "am" },
        { text: "Arabic", value: "ar" },
        { text: "Azerbaijani", value: "az" },
        { text: "Bengali", value: "bn" },
        { text: "Bosnian", value: "bs" },
        { text: "Bulgarian", value: "bg" },
        { text: "Chinese (Simplified)", value: "zh" },
        // AWS Translate does not support translating from zh to zh-TW
        // {text: 'Chinese (Traditional)', value: 'zh-TW'},
        { text: "Croatian", value: "hr" },
        { text: "Czech", value: "cs" },
        { text: "Danish", value: "da" },
        { text: "Dari", value: "fa-AF" },
        { text: "Dutch", value: "nl" },
        { text: "English", value: "en" },
        { text: "Estonian", value: "et" },
        { text: "Finnish", value: "fi" },
        { text: "French", value: "fr" },
        { text: "French (Canadian)", value: "fr-CA" },
        { text: "Georgian", value: "ka" },
        { text: "German", value: "de" },
        { text: "Greek", value: "el" },
        { text: "Hausa", value: "ha" },
        { text: "Hebrew", value: "he" },
        { text: "Hindi", value: "hi" },
        { text: "Hungarian", value: "hu" },
        { text: "Indonesian", value: "id" },
        { text: "Italian", value: "it" },
        { text: "Japanese", value: "ja" },
        { text: "Korean", value: "ko" },
        { text: "Latvian", value: "lv" },
        { text: "Malay", value: "ms" },
        { text: "Norwegian", value: "no" },
        { text: "Persian", value: "fa" },
        { text: "Pashto", value: "ps" },
        { text: "Polish", value: "pl" },
        { text: "Portuguese", value: "pt" },
        { text: "Romanian", value: "ro" },
        { text: "Russian", value: "ru" },
        { text: "Serbian", value: "sr" },
        { text: "Slovak", value: "sk" },
        { text: "Slovenian", value: "sl" },
        { text: "Somali", value: "so" },
        { text: "Spanish", value: "es" },
        { text: "Swahili", value: "sw" },
        { text: "Swedish", value: "sv" },
        { text: "Tagalog", value: "tl" },
        { text: "Tamil", value: "ta" },
        { text: "Thai", value: "th" },
        { text: "Turkish", value: "tr" },
        { text: "Ukrainian", value: "uk" },
        { text: "Urdu", value: "ur" },
        { text: "Vietnamese", value: "vi" }
      ],
      selectedTranslateLanguages: [],
      uploadErrorMessage: "",
      invalidFileMessage: "",
      invalidFileMessages: [],
      showInvalidFile: false,
      dismissSecs: 8,
      dismissCountDown: 0,
      executed_assets: [],
      workflow_status_polling: null,
      description:
        "Click Start Workflow to begin. Content analysis status will be shown after the workflow is started.",
      s3_destination: "s3://" + this.DATAPLANE_BUCKET,
    }
  },
  computed: {
    overlappingTerminologies() {
      // This function returns a list of terminologies that contain the translations for the same language.
      // flatten the array of TargetLanguageCodes arrays
      const language_codes = [].concat.apply([], this.customTerminology.map(x => x.TargetLanguageCodes))
      // get duplicate language codes in list
      let duplicate_language_codes = language_codes.sort().filter(function(item, pos, ary) {
        return item == ary[pos - 1];
      }).filter(function(item, pos, ary) {
        return !pos || item != ary[pos - 1];
      })
      // get the terminologies which contain duplicate language codes
      let overlapping_terminologies = []
      for (const i in duplicate_language_codes) {
        overlapping_terminologies = overlapping_terminologies.concat(this.customTerminology.filter(x => x.TargetLanguageCodes.includes(duplicate_language_codes[i])).map(x => x.Name))
      }
      // remove duplicate terminologies from the overlapping_terminologies list
      overlapping_terminologies = overlapping_terminologies.sort().filter(function(item, pos, ary) {
        return !pos || item != ary[pos - 1];
      })
      return overlapping_terminologies
    },
    overlappingParallelData() {
      // This function returns a list of parallel data sets that contain the translations for the same language.
      // flatten the array of TargetLanguageCodes arrays
      const language_codes = [].concat.apply([], this.parallelData.map(x => x.TargetLanguageCodes))
      // get duplicate language codes in list
      let duplicate_language_codes = language_codes.sort().filter(function(item, pos, ary) {
        return item == ary[pos - 1];
      }).filter(function(item, pos, ary) {
        return !pos || item != ary[pos - 1];
      })
      // get the parallel data sets which contain duplicate language codes
      let overlapping_language_codes = []
      for (const i in duplicate_language_codes) {
        overlapping_language_codes = overlapping_parallel_data.concat(this.parallelData.filter(x => x.TargetLanguageCodes.includes(duplicate_language_codes[i])).map(x => x.Name))
      }
      // remove duplicate parallel data from the overlapping_parallel_data list
      overlapping_language_codes = overlapping_language_codes.sort().filter(function(item, pos, ary) {
        return !pos || item != ary[pos - 1];
      })
      return overlapping_language_codes
    },

    // translateLanguageTags is the same as translateLanguages except
    // with keys and values flipped around. We need this field ordering
    // for the voerro-tags-input. The flipping is done in here as a computed property.
    translateLanguageTags() {
      return this.translateLanguages
        .map(x => {return {"text": x.value, "value": x.text}})
        //FIXME: filtering source languge from language tag list doesn't refresh 
        // tag picker in UI.  So, if source language is English to start, English is 
        // removed from the translation target languages.  When source language
        // is changed to Spanish, Engish is added back to the tags on the Vue 
        // Translation component but Engish tag is still missing on the tag
        // picker.  For now, leave the source language in the list.
        //.filter(x => x.text !== this.sourceLanguageCode)
    },
    ...mapState(['execution_history']),
    sourceLanguageCode() {
      return this.transcribeLanguage.split('-')[0]
    },
    textFormError() {
      if (this.enabledOperators.includes("Translate") && this.selectedTranslateLanguages.length === 0) {
        return "Choose at least one language.";
      }
      return "";
    },
    audioFormError() {
      // Validate transcribe is enabled if any text operator is enabled
      if (
        !this.enabledOperators.includes("Transcribe") &&
        (this.enabledOperators.includes("Translate") ||
          this.enabledOperators.includes("ComprehendEntities") ||
          this.enabledOperators.includes("ComprehendKeyPhrases"))
      ) {
        return "Transcribe must be enabled if any text operator is enabled.";
      }
      return "";
    },
    videoFormError() {
      // Validate face collection ID if face search is enabled
      if (this.enabledOperators.includes("faceSearch")) {
        // Validate that the collection ID is defined
        if (this.faceCollectionId === "") {
          return "Face collection name is required.";
        }

        // Validate that the collection ID matches required regex
        else if (new RegExp("[^a-zA-Z0-9_.\\-]").test(this.faceCollectionId)) {
          return "Face collection name must match pattern [a-zA-Z0-9_.\\\\-]+";
        }
        // Validate that the collection ID is not too long
        else if (this.faceCollectionId.length > 255) {
          return "Face collection name must have fewer than 255 characters.";
        }
      }
      if (this.enabledOperators.includes("genericDataLookup")) {
        // Validate that the collection ID is defined
        if (this.genericDataFilename === "") {
          return "Data filename is required.";
        }
        // Validate that the collection ID matches required regex
        else if (!new RegExp("^.+\\.json$").test(this.genericDataFilename)) {
          return "Data filename must have .json extension.";
        }
        // Validate that the data filename is not too long
        else if (this.genericDataFilename.length > 255) {
          return "Data filename must have fewer than 255 characters.";
        }
      }
      return "";
    },
    validForm() {
      let validStatus = true;
      if (
        this.invalid_file_types ||
        this.textFormError ||
        this.audioFormError ||
        this.videoFormError ||
        this.overlappingTerminologies.length > 0 ||
        this.overlappingParallelData > 0
      ) 
        validStatus = false;
      return validStatus;
    },
    workflowConfig() {
      return {
        "Name": "VODSubtitlesVideoWorkflow",
        "Configuration": {
          "defaultPrelimVideoStage2": {
            "Thumbnail": {
              "ThumbnailPosition": this.thumbnail_position.toString(),
              "MediaType": "Video",
              "Enabled": true
            },
            "Mediainfo": {"MediaType": "Video", "Enabled": true}
          },
          "MediaconvertStage2": {"Mediaconvert": {"MediaType": "Video", "Enabled": true}},
          "CaptionEditingWaitStage": {
            "Wait": {
              "MediaType": "MetadataOnly",
              "Enabled": this.enable_caption_editing
            }
          },
          "CaptionFileStage2": {
            "WebToSRTCaptions": {
              "MediaType": "MetadataOnly",
              "TargetLanguageCodes": Object.values(this.selectedTranslateLanguages.map(x => x.text)).filter(x => x !== this.sourceLanguageCode).concat(this.sourceLanguageCode),
              "Enabled": this.enabledOperators.includes("Translate")
            },
            "WebToVTTCaptions": {
              "MediaType": "MetadataOnly",
              "TargetLanguageCodes": Object.values(this.selectedTranslateLanguages.map(x => x.text)).filter(x => x !== this.sourceLanguageCode).concat(this.sourceLanguageCode),
              "Enabled": this.enabledOperators.includes("Translate")
            },
            "PollyWebCaptions": {
              "MediaType":"MetadataOnly",
              "Enabled": this.enabledOperators.includes("Translate"),
              "SourceLanguageCode": this.sourceLanguageCode
            }
          },
          "WebCaptionsStage2": {
            "WebCaptions": {
              "MediaType": "MetadataOnly",
              "SourceLanguageCode": this.sourceLanguageCode,
              "Enabled": this.enabledOperators.includes("Transcribe"),
            }
          },
          "TranslateStage2": {
            "Translate": {
              "MediaType":"Text",
              "Enabled": false,
            },
            "TranslateWebCaptions": {
              "MediaType":"MetadataOnly",
              "Enabled": this.enabledOperators.includes("Translate"),
              "TargetLanguageCodes": Object.values(this.selectedTranslateLanguages.map(x => x.text)).filter(x => x !== this.sourceLanguageCode),
              "SourceLanguageCode": this.sourceLanguageCode
            }
          },
          "defaultAudioStage2": {
            "TranscribeVideo": {
              "MediaType": "Audio",
              "Enabled": this.enabledOperators.includes("Transcribe"),
              "TranscribeLanguage": this.transcribeLanguage,
            }
          },
          "defaultTextSynthesisStage2": {"Polly": {"MediaType": "Text", "Enabled": false}},
          "defaultVideoStage2": {
            "faceDetection": {"MediaType": "Video", "Enabled": this.enabledOperators.includes("faceDetection")},
            "textDetection": {"MediaType": "Video", "Enabled": this.enabledOperators.includes("textDetection")},
            "celebrityRecognition": {"MediaType": "Video", "Enabled": this.enabledOperators.includes("celebrityRecognition")},
            "GenericDataLookup": {"MediaType": "Video", "Enabled": false},
            "labelDetection": {"MediaType": "Video", "Enabled": this.enabledOperators.includes("labelDetection")},
            "personTracking": {"MediaType": "Video", "Enabled": false},
            "Mediaconvert": {"MediaType": "Video", "Enabled": false},
            "contentModeration": {"MediaType": "Video", "Enabled": this.enabledOperators.includes("contentModeration")},
            "faceSearch": {
              "MediaType": "Video",
              "Enabled": this.enabledOperators.includes("faceSearch"),
              "CollectionId": this.faceCollectionId==="" ? "undefined" : this.faceCollectionId
            }
          },
          "defaultTextStage2": {
            "ComprehendEntities": {"MediaType": "Text", "Enabled": this.enabledOperators.includes("ComprehendEntities")},
            "ComprehendKeyPhrases": {"MediaType": "Text", "Enabled": this.enabledOperators.includes("ComprehendKeyPhrases")}
          }
        }
      }
    }
  },
  watch: {
    transcribeLanguage: function() {
      // Transcribe will fail if the custom vocabulary language
      // does not match the transcribe job language.
      // So, this function prevents users from selecting vocabularies
      // which don't match the selected Transcribe source language.
      this.customVocabularyList.map(item => {
        item.notEnabled=(item.language_code !== this.transcribeLanguage)
      })
    }
  },
  created: function() {
    if (this.$route.query.asset) {
      this.hasAssetParam = true;
      this.assetIdParam = this.$route.query.asset;
    }
  },
  mounted: function() {
    this.executed_assets = this.execution_history;
    this.pollWorkflowStatus();
    this.listVocabulariesRequest()
    this.listTerminologiesRequest()
    this.listParallelDataRequest()
  },
  beforeDestroy() {
    clearInterval(this.workflow_status_polling);
  },
  methods: {
    selectAll: function() {
      this.enabledOperators = [
        "labelDetection",
        "textDetection",
        "celebrityRecognition",
        "contentModeration",
        "faceDetection",
        "thumbnail",
        "Transcribe",
        "Translate",
        "Subtitles",
        "ComprehendKeyPhrases",
        "ComprehendEntities"
      ];
      this.show_disclaimer = true;
      this.create_video_stream = true;

    },
    clearAll: function (){
      this.enabledOperators = [];
      this.show_disclaimer = false;
      this.create_video_stream = false;
    },
    openWindow: function(url) {
      window.open(url);
    },
    countDownChanged(dismissCountDown) {
      this.dismissCountDown = dismissCountDown;
    },
    s3UploadError(error) {
      console.log(error);
      // display alert
      this.uploadErrorMessage = error;
      this.dismissCountDown = this.dismissSecs;
    },

    
    runWorkflow: async function (location) {
      const vm = this;
      let media_type = null;
      let s3Key = null;
      if ("key" in location) {
        media_type = location.type;
        s3Key = 'public/' + location.key; // add in public since amplify prepends that to all keys
      } else {
        media_type = this.$route.query.mediaType;
        s3Key = this.$route.query.s3key.split("/").pop();
      }
      let data = {};
      if (this.hasAssetParam) {
        if (media_type === "video") {
          data = vm.workflowConfig;
          data["Input"] = { AssetId: this.assetIdParam, Media: { Video: {} } };
        } else if (media_type === "image") {

          data = {
            Input: {
              AssetId: this.assetIdParam,
              Media: {
                Image: {}
              }
            },
            Name: "CasImageWorkflow",
            Configuration: {
              ValidationStage: {
                MediainfoImage: {
                  Enabled: true
                }
              },
              RekognitionStage: {
                faceSearchImage: {
                  Enabled: this.enabledOperators.includes("faceSearch"),
                  CollectionId:
                    this.faceCollectionId === ""
                      ? "undefined"
                      : this.faceCollectionId
                },
                labelDetectionImage: {
                  Enabled: this.enabledOperators.includes("labelDetection")
                },
                textDetectionImage: {
                  Enabled: this.enabledOperators.includes("textDetection")
                },
                celebrityRecognitionImage: {
                  Enabled: this.enabledOperators.includes(
                    "celebrityRecognition"
                  )
                },
                contentModerationImage: {
                  Enabled: this.enabledOperators.includes("contentModeration")
                },
                faceDetectionImage: {
                  Enabled: this.enabledOperators.includes("faceDetection")
                }
              }
            }
          };
        } else {
          vm.s3UploadError(
            "Unsupported media type, " + this.$route.query.mediaType + "."
          );
        }
      } else 
        if (media_type.match(/video/g) || 
            this.valid_media_types.includes(location.s3ObjectLocation.fields.key.split('.').pop().toLowerCase())) {
          // Create workflow config from user-specified options:
          data = vm.workflowConfig;
          // Add optional parameters to workflow config:
          if (this.customTerminology !== null) {
            data.Configuration.TranslateStage2.TranslateWebCaptions.TerminologyNames = this.customTerminology
          }
          if (this.parallelData != null) {
            data.Configuration.TranslateStage2.TranslateWebCaptions.ParallelDataNames = this.parallelData
          }
          if (this.customVocab !== null) {
            data.Configuration.defaultAudioStage2.Transcribe.VocabularyName = this.customVocab
          }
          if (this.existingSubtitlesFilename == "") {
            if ("ExistingSubtitlesObject" in data.Configuration.WebCaptionsStage2.WebCaptions){
                delete data.Configuration.WebCaptionsStage2.WebCaptions.ExistingSubtitlesObject
            }
          }
          else {
            data.Configuration.WebCaptionsStage2.WebCaptions.ExistingSubtitlesObject = {}
            data.Configuration.WebCaptionsStage2.WebCaptions.ExistingSubtitlesObject.Bucket=this.DATAPLANE_BUCKET
            data.Configuration.WebCaptionsStage2.WebCaptions.ExistingSubtitlesObject.Key=this.customTerminology,
            data.Configuration.WebCaptionsStage2.WebCaptions.ExistingSubtitlesObject.Key=this.parallelData
          }
          // Add input parameter to workflow config:
          data["Input"] = {
            Media: {
              Video: {
                S3Bucket: this.DATAPLANE_BUCKET,
                S3Key: s3Key
              }
            }
          };
        } else if (media_type === "application/json") {
          // JSON files may be uploaded for the genericDataLookup operator, but
          // we won't run a workflow for json file types.
          console.log("Data file has been uploaded to s3://" + s3key);
          return;
        } else if (media_type === '' && (s3Key.split('.').pop().toLowerCase() == 'vtt')) {
          // VTT files may be uploaded for the Transcribe operator, but
          // we won't run a workflow for VTT file types.
          console.log("VTT file has been uploaded to s3://" + s3Key);
          return;
        } else {
          vm.s3UploadError("Unsupported media type: " + media_type + ".");
        }
      
      console.log(JSON.stringify(data));
      // TODO: Should this be its own function?

      let apiName = 'mieWorkflowApi'
      let path = 'workflow/execution'
      let requestOpts = {
          headers: {
            'Content-Type': 'application/json'
          },
          response: true,
          body: data,
          queryStringParameters: {} // optional
      };
      try {
        let response = await this.$Amplify.API.post(apiName, path, requestOpts);
        let asset_id = response.data.AssetId;
        let wf_id = response.data.Id;
        //console.log("Media assigned asset id: " + asset_id);
        let executed_asset = {
            asset_id: asset_id,
            file_name: s3Key,
            workflow_status: "",
            state_machine_console_link: "",
            wf_id: wf_id
          };
        vm.executed_assets.push(executed_asset);
        vm.getWorkflowStatus(wf_id);
        this.hasAssetParam = false;
        this.assetIdParam = "";
      } catch (error) {
        alert(
          "ERROR: Failed to start workflow. Check Workflow API logs."
        );
        console.log(error)
      }
    },
    async getWorkflowStatus(wf_id) {
      const vm = this;
      let apiName = 'mieWorkflowApi'
      let path =  "workflow/execution/" + wf_id
      let requestOpts = {
        headers: {},
        response: true,
        queryStringParameters: {} // optional
      };
      try {
        let response = await this.$Amplify.API.get(apiName, path, requestOpts);
        for (let i = 0; i < vm.executed_assets.length; i++) {
          if (vm.executed_assets[i].wf_id === wf_id) {
            vm.executed_assets[i].workflow_status = response.data.Status;
            vm.executed_assets[i].state_machine_console_link =
            "https://" + this.AWS_REGION + ".console.aws.amazon.com/states/home?region=" + this.AWS_REGION + "#/executions/details/" + response.data.StateMachineExecutionArn;
            break;
          }
        }
      this.$store.commit("updateExecutedAssets", vm.executed_assets);
      } catch (error) {
        console.log ("ERROR: Failed to get workflow status");
        console.log(error)
      }
    },
    pollWorkflowStatus() {
      // Poll frequency in milliseconds
      const poll_frequency = 5000;
      this.workflow_status_polling = setInterval(() => {
        this.executed_assets.forEach(item => {
          if (
            item.workflow_status === "" ||
            item.workflow_status === "Started" ||
            item.workflow_status === "Queued"
          ) {
            this.getWorkflowStatus(item.wf_id);
          }
        });
      }, poll_frequency);
    },
    uploadFiles() {
      let key = 'upload/' + this.file.name
      let vm = this // hate this, not sure how to get correct scope inside the progressCallback method
      console.log('creds', this.$Amplify.Auth.currentSession())
      this.$Amplify.Storage.put(key, this.file, {
        level: 'public', // not actually public in the S3 sense, this is just an amplify construct
        progressCallback(progress) {
          vm.isUploading = true
          vm.uploadValue = 0
          let uploadedDec = (progress.loaded / progress.total) * 100
          vm.uploadValue = uploadedDec
        },
      }).then(function(result) {
              vm.isUploading = null
              vm.uploadValue = null
              let location = result
              location.type = vm.file.type
              vm.runWorkflow(location)
              vm.file = null
        }
      ).catch (function(err) {
          alert(err)
          vm.isUploading = null
          vm.uploadValue = null
          vm.file = null

      });
    },
    clearHistory() {
      this.executed_assets = [];
      this.$store.commit("updateExecutedAssets", this.executed_assets);
    },
    pollVocabularyStatus() {
      // Poll frequency in milliseconds
      const poll_frequency = 10000;
      this.vocab_status_polling = setInterval(() => {
        this.listVocabulariesRequest();
      }, poll_frequency)
    },
    listTerminologiesRequest: async function () {
      
      let apiName = 'mieWorkflowApi'
      let path = 'service/translate/list_terminologies'
      
      let requestOpts = {
          headers: {
            'Content-Type': 'application/json'
          },
          response: true
      };
      try {
        let response = await this.$Amplify.API.get(apiName, path, requestOpts);
        this.customTerminologyList  = response.data['TerminologyPropertiesList']
          // .map(terminology => {
          //   return {
          //     'Name': terminology.Name,
          //     'SourceLanguageCode': terminology.SourceLanguageCode,
          //     'TargetLanguageCodes': terminology.TargetLanguageCodes
          //   }
          // })
        
      } catch (error) {
        alert(
          "ERROR: Failed to start workflow. Check Workflow API logs."
        );
        console.log(error)
      }
    },
    fileAdded: function( file )
    {
      let errorMessage = '';
      console.log(file.type)
      if (!(file.type).match(/image\/.+|video\/.+|application\/json/g) && !(file.name.split('.').pop().toLowerCase() == 'vtt') && !this.valid_media_types.includes(file.name.split('.').pop().toLowerCase())) {
        if (file.type === "") {
          console.log("here")
          errorMessage = "Unsupported file type: unknown";
        }
        else
          errorMessage = "Unsupported file type: " + file.type;
        this.invalidFileMessages.push(errorMessage);
        this.showInvalidFile = true
      }


      // if this is a VTT file, auto-fill the vtt file input for transcribe
      if ((file.name.split('.').pop().toLowerCase() == 'vtt')) {
        if (this.existingSubtitlesFilename == ""){
          this.existingSubtitlesFilename = file.name
        }

      }
    },
    fileRemoved: function( file )
    {
      let errorMessage = '';
      if (!(file.type).match(/image\/.+|video\/.+|application\/json/g)) {
        if (file.type === "")
          errorMessage = "Unsupported file type: unknown";
        else
          errorMessage = "Unsupported file type: " + file.type;
      }
      this.invalidFileMessages = this.invalidFileMessages.filter(function(value){ return value != errorMessage})
      if (this.invalidFileMessages.length === 0 ) this.showInvalidFile = false;

      // if this is a VTT file, and the auto-filled file is removed, then remove the autofill
      if ((file.name.split('.').pop().toLowerCase() == 'vtt')) {
        if (this.existingSubtitlesFilename == file.name) {
          this.existingSubtitlesFilename = ""
        }
      }
    },
    listVocabulariesRequest: async function () {
      
      let apiName = 'mieWorkflowApi'
      let path = 'service/transcribe/list_vocabularies'
      
      let requestOpts = {
          headers: {
            'Content-Type': 'application/json'
          },
          response: true
      };
      try {
        let response = await this.$Amplify.API.get(apiName, path, requestOpts);
        this.customVocabularyList = response.data["Vocabularies"].map(({VocabularyName, VocabularyState, LanguageCode}) => ({
            name: VocabularyName,
            status: VocabularyState,
            language_code: LanguageCode,
            name_and_status: VocabularyState === "READY" ?
                VocabularyName+" ("+LanguageCode+")" :
                VocabularyName + " [" + VocabularyState + "]",
            notEnabled: (VocabularyState === "PENDING" || LanguageCode !== this.transcribeLanguage)
          }))
          // if any vocab is PENDING, then poll status until it is not PENDING. This is necessary so custom vocabs become selectable in the GUI as soon as they become ready.
          if (this.customVocabularyList.filter(item => item.status === "PENDING").length > 0) {
            if (this.vocab_status_polling == null) {
              this.pollVocabularyStatus();
            }
          } else {
            if (this.vocab_status_polling != null) {
              clearInterval(this.vocab_status_polling)
              this.vocab_status_polling = null
            }
          }

        
      } catch (error) {
        alert(
          "ERROR: Failed to get vocabularies."
        );
        console.log(error)
      }
    },
    listParallelDataRequest: async function () {
      
      let apiName = 'mieWorkflowApi'
      let path = 'service/translate/list_parallel_data'
      
      let requestOpts = {
          headers: {
            'Content-Type': 'application/json'
          },
          response: true
      };
      try {
        let response = await this.$Amplify.API.get(apiName, path, requestOpts);
        console.log(response)
        this.parallelDataList  = response.data['ParallelDataPropertiesList'].map(parallel_data => {
            return {
              'Name': parallel_data.Name,
              'SourceLanguageCode': parallel_data.SourceLanguageCode,
              'TargetLanguageCodes': parallel_data.TargetLanguageCodes
            }
          })
        
      } catch (error) {
        console.log("ERROR: Failed to get parallel data. Check Workflow API logs.");
        console.log(error)
      }
    }
  }
  
};
</script>
<style>
input[type="text"] {
  width: 100%;
  padding: 12px 20px;
  margin: 8px 0;
  box-sizing: border-box;
}

label {
  font-weight: bold;
}

.note {
  color: red;
  font-family: "Courier New";
}
</style>
