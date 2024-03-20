/*
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
*/
import { createApp } from 'vue'
import VueHighlightJS from 'vue-highlightjs'
import { BootstrapVue, BootstrapVueIcons } from 'bootstrap-vue'

import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'
import 'dropzone/dist/dropzone.css'
import "highlight.js/styles/github.css"

import App from './App.vue'
import store from './store'
import router from './router.js'
import { Amplify } from "aws-amplify";
import * as AmplifyModules from "aws-amplify";
import { AmplifyPlugin } from "aws-amplify-vue";

const app = createApp({
  router,
  ...App
})

const getRuntimeConfig = async () => {
  const runtimeConfig = await fetch('/runtimeConfig.json');
  return await runtimeConfig.json()
};

getRuntimeConfig().then(function(json) {
  const awsconfig = {
    Auth: {
      region: json.AWS_REGION,
      userPoolId: json.USER_POOL_ID,
      userPoolWebClientId: json.USER_POOL_CLIENT_ID,
      identityPoolId: json.IDENTITY_POOL_ID
    },
    Storage: {
      AWSS3: {
        bucket: json.DATAPLANE_BUCKET,
        region: json.AWS_REGION
      }
    },
    API: {
      endpoints: [
        {
          name: "search",
          endpoint: json.SEARCH_ENDPOINT,
          service: "es",
          region: json.AWS_REGION
        },
        {
          name: "mieWorkflowApi",
          endpoint: json.WORKFLOW_API_ENDPOINT,
          service: "execute-api",
          region: json.AWS_REGION
        },
        {
          name: "mieDataplaneApi",
          endpoint: json.DATAPLANE_API_ENDPOINT,
          service: "execute-api",
          region: json.AWS_REGION
        }
      ]
    }
  };
  console.log("Runtime config: " + JSON.stringify(json));
  Amplify.configure(awsconfig);
  app.mixin({
    data() {
      return {
        // Distribute runtime configs into every Vue component
        SEARCH_ENDPOINT: json.SEARCH_ENDPOINT,
        DATAPLANE_API_ENDPOINT: json.DATAPLANE_API_ENDPOINT,
        DATAPLANE_BUCKET: json.DATAPLANE_BUCKET,
        WORKFLOW_API_ENDPOINT: json.WORKFLOW_API_ENDPOINT,
        AWS_REGION: json.AWS_REGION
      }
    },
  });

  app.use(AmplifyPlugin, AmplifyModules);
  app.use(BootstrapVue);
  app.use(store);
  app.use(BootstrapVueIcons);
  app.use(VueHighlightJS)

  router.beforeResolve(async (to, from, next) => {
    if (to.matched.some(record => record.meta.requiresAuth)) {
      try {
        await app.prototype.$Amplify.Auth.currentAuthenticatedUser();
        next();
      } catch (e) {
        console.log(e);
        next({
          path: "/",
          query: {
            redirect: to.fullPath
          }
        });
      }
    }
    console.log(next);
    next();
  });

  app.mount('#app')
});
