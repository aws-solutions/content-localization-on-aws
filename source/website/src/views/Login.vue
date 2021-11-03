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
    <amplify-authenticator></amplify-authenticator>
  </div>
</template>

<script>
//-----------------------------------------------------------//
// Hack to work around a bug in amplify-authenticator, which makes it so it
// doesn't notice if a username is autofilled rather than being typed in.
// This work around enables the 1password browser plugin to autofill
// username and password.
//
// See https://github.com/aws-amplify/amplify-js/issues/4374
//
// This hack can be removed once the issue is resolved.
function patchSignIn () {
  // monkey-patch the UsernameField component, and add a watcher to make it properly emit a changed
  // event when the username field changes
  let usernameComponent = Vue.component('amplify-username-field');
  let watches = usernameComponent.options.watch = usernameComponent.options.watch || {};
  watches.username = function () {
    this.usernameChanged()
  };
  watches.email = function () {
    this.emailChanged()
  }
}
import Vue from 'vue'
patchSignIn();
//-----------------------------------------------------------//

import { AmplifyEventBus } from "aws-amplify-vue";

export default {
  name: "Login",
  data() {
    return {};
  },
  mounted() {
    AmplifyEventBus.$on("authState", eventInfo => {
      if (eventInfo === "signedIn") {
        this.$router.push({ name: "collection" });
      } else if (eventInfo === "signedOut") {
        this.$router.push({ name: "Login" });
      }
    });
  },
  created() {
    this.getLoginStatus()
  },
  methods: {
    getLoginStatus () {
      this.$Amplify.Auth.currentSession().then(data => {
        this.session = data;
        if (this.session == null) {
          console.log('user must login')
        } else {
          this.$router.push({name: "collection"})
        }
      })
    }
  }
};
</script>

<style scoped>
</style>
