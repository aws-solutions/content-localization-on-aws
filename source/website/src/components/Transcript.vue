<!-- 
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
-->

<template>
  <div>
    <div v-if="noTranscript === true">
      No transcript found for this asset
    </div>
    <div v-if="isBusy">
      <b-spinner
        variant="secondary"
        label="Loading..."
      />
      <p class="text-muted">
        (Loading...)
      </p>
    </div>
    <div v-else>
      {{ transcript }}
      <br>
      <b-button v-if="transcript.length > 0" id="downloadTranscript" size="sm" class="mb-2" @click="downloadTranscript()">
        <b-icon icon="download" color="white"></b-icon> Download
      </b-button>
    </div>
  </div>
</template>

<script>
export default {
  name: "Transcript",
  data() {
    return {
      transcript: "",
      isBusy: false,
      operator: "transcript",
      noTranscript: false
    }
  },
  deactivated: function () {
    this.transcript = ""
    this.noTranscript = false
    console.log('deactivated component:', this.operator)
  },
  activated: function () {
    console.log('activated component:', this.operator);
    this.fetchAssetData();
  },
  beforeDestroy: function () {
    this.transcript = ''
  },
  methods: {
    async fetchAssetData () {
      let query = 'AssetId:'+this.$route.params.asset_id+ ' _index:mievideotranscript';
      let apiName = 'search';
      let path = '/_search';
      let apiParams = {
        headers: {'Content-Type': 'application/json'},
        queryStringParameters: {'q': query, 'default_operator': 'AND', 'size': 10000}
      };
      let response = await this.$Amplify.API.get(apiName, path, apiParams);
      if (!response) {
        this.showElasticSearchAlert = true
      }
      else {
        let result = await response;
        let data = result.hits.hits;
        if (data.length === 0) {
          this.noTranscript = true
        }
        else {
          this.noTranscript = false;
          for (let i = 0, len = data.length; i < len; i++) {
            if ('transcript' in data[i]._source) {
              this.transcript = this.transcript.concat(data[i]._source.transcript + " ")
              this.noTranscript = false;
            }

          }
        }
        this.isBusy = false
      }
    },
    downloadTranscript() {
      const blob = new Blob([this.transcript], {type: 'text/plain', endings:'native'});
      const a = document.createElement('a');
      a.download = "transcript.txt";
      a.href = window.URL.createObjectURL(blob);
      a.dataset.downloadurl = ['text/json', a.download, a.href].join(':');
      const e = new MouseEvent('click', { view: window });
      a.dispatchEvent(e);

    },
  }
}
</script>
