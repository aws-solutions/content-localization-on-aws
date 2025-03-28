<!-- 
  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
  SPDX-License-Identifier: Apache-2.0
-->

<template>
  <div>
    <div class="headerTextBackground">
      <HeaderView :is-collection-active="true" />
      <b-container fluid>
        <b-alert
          v-model="showElasticSearchAlert"
          variant="danger"
          dismissible
        >
          Elasticsearch error. Please check browser and elasticsearch access logs.
        </b-alert>
        <b-alert
          v-model="showDataplaneAlert"
          variant="danger"
          dismissible
        >
          Dataplane Error. Please check browser and dataplane logs.
        </b-alert>
        <b-alert
          v-model="showDeletedAlert"
          variant="success"
          dismissible
          fade
        >
          Successfully Deleted Asset
        </b-alert>
        <b-row align-h="center">
          <h1>Media Collection</h1>
        </b-row>
        <b-row
          align-h="center"
          class="tagline"
        >
          <b>Discover insights in your media by searching for keywords, objects, or even people.</b>
        </b-row>
        <b-row
          class="my-1"
          align-v="center"
          align-h="center"
        >
          <b-col sm="5">
            <input
              v-model="user_defined_query"
              type="text"
              placeholder="Search Collection..."
              @keyup.enter="searchCollection"
            >
          </b-col>
          <b-col sm="1">
            <b-button
              size="lg"
              @click="searchCollection"
            >
              Search
            </b-button>
          </b-col>
        </b-row>
      </b-container>
    </div>
    <b-container
      fluid
      class="resultsTable"
    >
      <b-row>
        <b-col>
          <div>
            <div class="column">
              <b-row class="my-1">
                <b-col>
                  <b-table
                    v-model:sort-by="sortBy"
                    v-model:sort-desc="sortDesc"
                    striped
                    hover
                    fixed
                    responsive
                    show-empty
                    :fields="fields"
                    :items="asset_list"
                    :current-page="currentPage"
                    :per-page="perPage"
                  >
                    <template #cell(Thumbnail)="data">
                      <VideoThumbnail
                        :thumbnail-i-d="data.item.thumbnailID"
                        :signed-url="data.item.signedUrl"
                      />
                    </template>
                    <template #cell(Created)="data">
                      {{ data.item.Created.toLocaleDateString() }}<br>
                      {{ data.item.Created.toLocaleTimeString() }}
                    </template>
                    <template #cell(status)="data">
                      <!-- open link in new tab -->
                      <a v-if="data.item.status !== 'Queued'" href="" @click.stop.prevent="openWindow(data.item.state_machine_console_link)">{{ data.item.status }}</a>
                      <div v-if="data.item.status === 'Queued'">
                        {{ data.item.status }}
                      </div>
                    </template>
                    <template #cell(Actions)="data">
                      <!-- //NOSONAR --> <b-link
                                           :href="(`/analysis/${data.item.asset_id}`)"
                                         >
                                           Analyze
                                         </b-link>
                      <br>
                      <b-link
                        class="text-danger"
                        @click="deleteAsset(`${data.item.asset_id}`)"
                      >
                        Delete
                      </b-link>
                    </template>
                  </b-table>
                  <div
                    v-if="noAssets"
                  >
                    <p>
                      Looks like no assets have been uploaded! Try uploading <a href="upload" rel="noopener noreferrer">here</a>.
                    </p>
                  </div>
                  <div
                    v-if="isBusy"
                    class="wrapper"
                  >
                    <Loading v-if="isBusy" />
                    <p class="text-muted">
                      (Loading...)
                    </p>
                  </div>
                </b-col>
              </b-row>
              <b-row align-h="center">
                <b-pagination
                  v-model="currentPage"
                  :total-rows="totalRows"
                  :per-page="perPage"
                  class="justify-content-center"
                />
              </b-row>
            </div>
          </div>
        </b-col>
      </b-row>
    </b-container>
  </div>
</template>

<script>
  import HeaderView from '@/components/HeaderView.vue'
  import VideoThumbnail from '@/components/VideoThumbnail.vue'
  import Loading from '@/components/Loading.vue'

  export default {
    name: "CollectionView",
    components: {
      HeaderView,
      Loading,
      VideoThumbnail
    },
    data() {
      return {
        showElasticSearchAlert: false,
        showDataplaneAlert: false,
        showDeletedAlert: 0,
        noAssets: null,
        currentPage: 1,
        perPage: 10,
        isBusy: false,
        user_defined_query: "",
        asset_list: [],
        sortBy: 'Created',
        sortDesc: true,
        fields: [
            {
              'Thumbnail': {
              label: "Thumbnail",
              sortable: false
              }
            },
            {
              'Filename': {
              label: "File Name",
              sortable: true,
              tdClass: ["tableWordWrap"]
              }
            },
            {
              'status': {
              label: "Status",
              sortable: true,
              tdClass: ["tableWordWrap"]
              }
            },
            {
            'asset_id': {
              label: 'Asset ID',
              sortable: false,
              tdClass: ["tableWordWrap"]
              }
            },
            {
              'Created': {
              label: "Created",
              sortable: true,
              tdClass: ["tableWordWrap"]
              }
            },
            {
              'Actions': {
              label: 'Actions',
              sortable: false
              }
            }
        ]
      }
    },
    computed: {
      totalRows() {
        return this.asset_list.length
      }
    },
    created: function () {
      this.isBusy = true;
      this.retrieveAndFormatAsssets()
    },
    methods: {
      openWindow: function (url) {
        window.open(url, "_blank", "noopener,noreferer");
      },
      async deleteAsset(assetId) {
        let apiName = 'mieDataplaneApi'
        let path = 'metadata/' + assetId
        let requestOpts = {
          response: true,
        };
        try {
          await this.$Amplify.API.del(apiName, path, requestOpts);
          this.showDeletedAlert = 5;
          this.asset_list = [];
          this.retrieveAndFormatAsssets()
        } catch (error) {
          this.showDataplaneAlert = true
          console.log(error)
        }
      },
      async elasticsearchQuery (query) {
            let apiName = 'search';
            let path = '/_search';
            let apiParams = {
              headers: {'Content-Type': 'application/json'},
              body: {
              "aggs" : {
                "distinct_assets" : {
                  "terms" : { "field" : "AssetId.keyword", "size" : 10000 }
                }
                }
              },
              queryStringParameters: {'q': query, '_source': 'AssetId'}
            };
            let response = await this.$Amplify.API.post(apiName, path, apiParams);
            if (!response) {
              this.showElasticSearchAlert = true
            }
            else {
              this.noAssets = false;
              return await response;
        }
      },
      async searchCollection () {
          this.noSearchResults = false;
          this.isBusy = true;
          let query = this.user_defined_query;
          // if search is empty string then get asset list from dataplane instead of Elasticsearch.
          if (query === "") {
            this.showElasticSearchAlert = false;
            this.asset_list = [];
            this.retrieveAndFormatAsssets();
            this.isBusy = false;
            return
          }

          // Get the list of assets that contain metadata matching the user-specified search query.
          let elasticData = await this.elasticsearchQuery(query);
          if (elasticData.hits.total === 0) {
            // the search returned no data
            this.asset_list = [];
            this.noSearchResults = true;
            this.isBusy = false;
          }
          else {
            let assets = [];
            this.asset_list = [];
            this.noSearchResults = false;
            let buckets = elasticData.aggregations.distinct_assets.buckets;
            for (let i = 0, len = buckets.length; i < len; i++) {
              let assetId = buckets[i].key;
              let assetInfo = await this.getAssetInformation(assetId);
              if (assetInfo !== null) {
                assets.push(assetInfo)
              }
          }
          if (assets.length === 0) {
            this.noSearchResults = true;
            this.isBusy = false
          }
          else {
            this.pushAssetsToTable(assets);
            this.isBusy = false
          }
        }
      },
      async getAssetWorkflowStatus (assetId) {
        let apiName = 'mieWorkflowApi'
        let path = 'workflow/execution/asset/' + assetId
        let requestOpts = {
          response: true,
        };
        try {
          let response = await this.$Amplify.API.get(apiName, path, requestOpts);
          return response.data
        } catch (error) {
          console.log(error)
        }
      },
      async getAssetThumbnail (bucket, s3Key) {
        const data = { "S3Bucket": bucket, "S3Key": s3Key };
        let apiName = 'mieDataplaneApi'
        let path = 'download'
        let requestOpts = {
          body: data,
          response: true,
          responseType: 'text'
        };
        try {
          let response = await this.$Amplify.API.post(apiName, path, requestOpts);
          return response.data
        } catch (error) {
          this.showDataplaneAlert = true
          console.log(error)
        }
      },
      async getAssetInformation (assetId) {
        let apiName = 'mieDataplaneApi'
        let path = 'metadata/' + assetId
        let requestOpts = {
          response: true,
        };
        try {
          let response = await this.$Amplify.API.get(apiName, path, requestOpts);
          return response.data
        } catch (error) {
          this.showDataplaneAlert = true
          console.log(error)
        }
      },
      async fetchAssets () {
        let apiName = 'mieDataplaneApi'
        let path = 'metadata'
        let requestOpts = {
          response: true,
        };
        try {
          let response = await this.$Amplify.API.get(apiName, path, requestOpts);
          return response.data
        } catch (error) {
          this.showDataplaneAlert = true
          console.log(error)
        }
      },
      async pushAssetsToTable(assets) {
        for (let i = 0, len = assets.length; i < len; i++) {
          let assetId;
          if (typeof assets[i] === 'object') {
            // If the asset list is coming from Elasticsearch, we get the assetId like this:
            assetId = assets[i].asset_id
          } else {
            // If the asset list is coming from the dataplaneapi, we get the assetId like this:
            assetId = assets[i]
          }
          // Invoke an asynchronous task to add assets to the table in parallel so the table updates
          // as fast as possible. For large media collections this may take several seconds.
          this.pushAssetToTable(assetId)
        }
      },
      async pushAssetToTable (assetId) {
        const assetInfo = await this.getAssetInformation(assetId);
        let created = new Date(0);
        created.setUTCSeconds(assetInfo.results.Created);
        const metadata_folder = "/private/assets/"+assetId
        const source_bucket = assetInfo.results.S3Bucket;
        const source_key = assetInfo.results.S3Key;
        let s3Uri = 's3://' + this.DATAPLANE_BUCKET + '/' + metadata_folder;
        const filename = source_key.split("/").pop();
        // The thumbnail is created by Media Convert, see:
        // source/operators/thumbnail/start_thumbnail.py
        let thumbnailS3Key = 'private/assets/' + assetId + '/' + filename.substring(0, filename.lastIndexOf(".")) + '_thumbnail.0000001.jpg';
        let thumbnailS3Bucket = this.DATAPLANE_BUCKET
        // If it's an image then Media Convert won't create a thumbnail.
        // In that case we use the uploaded image as the thumbnail.
        const supported_image_types = [".jpg", ".jpeg", ".tif", ".tiff", ".png", ".apng", ".gif", ".bmp", ".s gvg"];
        const media_type = filename.substring(filename.lastIndexOf(".")).toLowerCase();
        if (supported_image_types.includes(media_type)) {
          // use the uploaded image as a thumbnail
          thumbnailS3Key = source_key;
          thumbnailS3Bucket = source_bucket;
        }
        let [thumbnail, workflowStatus] = await Promise.all([this.getAssetThumbnail(thumbnailS3Bucket, thumbnailS3Key), this.getAssetWorkflowStatus(assetId)]);
        if (workflowStatus[0] && thumbnail)
        {
          this.asset_list.push({
            asset_id: assetId,
            Created: created,
            Filename: filename,
            status: workflowStatus[0].Status,
            state_machine_console_link: "https://" + this.AWS_REGION + ".console.aws.amazon.com/states/home?region=" + this.AWS_REGION + "#/executions/details/" + workflowStatus[0].StateMachineExecutionArn,
            s3_uri: s3Uri,
            signedUrl: thumbnail,
            thumbnailID: '_' + assetId,
            Thumbnail: '',
            Actions: 'Run'
          })
        }
      },

      async retrieveAndFormatAsssets () {
        let data = await this.fetchAssets();
        let assets = data.assets;
        if (assets.length === 0) {
          this.noAssets = true;
          this.noSearchResults = false;
          this.isBusy = false;
        }
        else {
          this.noAssets = false;
          this.pushAssetsToTable(assets);
          this.isBusy = false
        }
      }
    }
  }
</script>

<style>
  td {
    vertical-align: middle;
  }
  .headerTextBackground {
    background-color: #191918;
    max-width: 100%;
    height: auto;
    padding-bottom: 1%;
  }
  .resultsTable {
    padding-top: 1%;
  }
  h1 {
    color: #ED900E;
  }
  a {
    color: #ED900E;
  }
  .tagline {
    color: white
  }
  .btn-orange {
    color: #ED900E
  }
  .btn-red {
    color: red
  }
  .tableWordWrap {
    white-space:normal;
    word-break:break-all;
    overflow: hidden;
    text-overflow:ellipsis;
  }
</style>
