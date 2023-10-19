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
  <b-container fluid>
    <b-row
      align-v="center"
      class="my-1"
    >
      <b-col>
        <label>
          <router-link :to="{ name: 'upload', query: { asset: $route.params.asset_id, mediaType: mediaType, s3key: s3Uri}}">Perform Additional Analysis</router-link>
        </label>
        <br>
        <label>Asset ID:</label>
        {{ $route.params.asset_id }}
        <br>
        <label>Filename:&nbsp;</label>
        <!-- //NOSONAR --> <a
          :href="videoUrl" rel="noopener noreferrer"
          download
        >
          {{ filename }}
        </a>
        <br>
        <div
          v-if="isBusy === false"
          class="wrapper"
        >
          <b-row>
            <b-col>
              <div v-if="duration !== 'undefined'">
                <label>Video duration:</label>
                {{ duration }}
              </div>
              <div v-if="format !== 'undefined'">
                <label>Video format:</label>
                {{ format }}
              </div>
              <div v-if="file_size !== 'undefined'">
                <label>Video file size:</label>
                {{ file_size }} MB
              </div>
              <div v-if="overall_bit_rate !== 'undefined'">
                <label>Video bit rate:</label>
                {{ overall_bit_rate }} bps
              </div>
              <div v-if="frame_rate !== 'undefined'">
                <label>Video frame rate:</label>
                {{ frame_rate }} fps
              </div>
              <div v-if="width !== 'undefined' && height !== 'undefined' ">
                <label>Video resolution:</label>
                {{ width }} x {{ height }}
              </div>
            </b-col>
            <b-col>
              <div v-if="other_bit_rate !== 'undefined'">
                <label>Audio bit rate:</label>
                {{ other_bit_rate }}
              </div>
              <div v-if="other_sampling_rate !== 'undefined'">
                <label>Audio sampling rate:</label>
                {{ other_sampling_rate }}
              </div>
              <div v-if="other_language !== 'undefined'">
                <label>Audio Language:</label>
                {{ other_language }}
              </div>
              <div v-if="encoded_date !== 'undefined'">
                <label>Encoded date:</label>
                {{ encoded_date }}
              </div>
              <div v-for="property in operator_info" :key="property.name">
                <div v-if="property.value !== ''">
                  <label>{{ property.name }}:</label>
                  {{ property.value }}
                </div>
              </div>
            </b-col>
          </b-row>
        </div>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
  import { mapState } from 'vuex'

  export default {
    name: 'MediaSummary',
    props: ['s3Uri','filename','videoUrl', 'mediaType'],
    data () {
      return {
        duration: "undefined",
        elasticsearch_data: [],
        mediainfo_data: [],
        format: "undefined",
        file_size: "undefined",
        overall_bit_rate: "undefined",
        frame_rate: "undefined",
        width: "undefined",
        height: "undefined",
        other_bit_rate: "undefined",
        other_sampling_rate: "undefined",
        other_language: "undefined",
        encoded_date: "undefined",
        isBusy: false,
      }
    },
    computed: {
      ...mapState(['operator_info']),
    },
    deactivated: function () {
      this.lineChart = Object
    },
    mounted: function () {
      this.fetchAssetData();
    },
    beforeDestroy: function () {
    },
    methods: {
      async fetchAssetData () {
        this.isBusy = true;
        let query = 'AssetId:'+this.$route.params.asset_id+' Operator:mediainfo';
        let apiName = 'search';
        let path = '/_search';
        let apiParams = {
          headers: {'Content-Type': 'application/json'},
          queryStringParameters: {'q': query, 'default_operator': 'AND', 'size': 10000}
        };
        let response = await this.$Amplify.API.get(apiName, path, apiParams);
        if (!response) {
          this.showElasticSearchAlert = true;
          return;
        }
        let result = await response;
        let data = result.hits.hits;
        let es_data = data.map(d => d._source);
        this.elasticsearch_data = JSON.parse(JSON.stringify(es_data));
        const trackGeneral = this.elasticsearch_data.find(x => x.track_type === "General");
        const trackVideo = this.elasticsearch_data.find(x => x.track_type === "Video");
        const trackAudio = this.elasticsearch_data.find(x => x.track_type === "Audio");

        const promote = (function (track, prop, mapFn) {
          if (prop in track) {
            this[prop] = mapFn(track[prop]);
          }
        }).bind(this);

        if (trackGeneral !== undefined) {
          if ("duration" in trackGeneral) {
            let seconds = trackGeneral.duration / 1000;
            if (seconds >= 3600) {
              this.duration = new Date(seconds * 1000).toISOString().substring(11, 19);
            } else {
              // drop hours portion if time is less than 1 hour
              this.duration = new Date(seconds * 1000).toISOString().substring(14, 19);
            }
          }
          promote(trackGeneral, "format", value => value);
          promote(trackGeneral, "file_size", value => (value / 1000 / 1000).toFixed(2));
          promote(trackGeneral, "overall_bit_rate", value => value);
          promote(trackGeneral, "frame_rate", value => value);
        }
        if (trackVideo !== undefined) {
          promote(trackVideo, "width", value => value);
          promote(trackVideo, "height", value => value);
        }
        if (trackAudio !== undefined) {
          promote(trackAudio, "other_bit_rate", value => value[0]);
          promote(trackAudio, "other_sampling_rate", value => value[0]);
          promote(trackAudio, "other_language", value => value[0]);
          promote(trackAudio, "encoded_date", value => value);
        }
        this.isBusy = false
      }
    }
  }
</script>
