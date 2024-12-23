// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import Vue from 'vue'
import VueRouter from 'vue-router'
import Analysis from '@/views/Analysis.vue'
import Upload from '@/views/UploadToAWSS3.vue'
import Collection from '@/views/Collection.vue'
import Login from '@/views/Login.vue'

Vue.use(VueRouter);

const routes = [
  {
    path: '/collection',
    name: 'collection',
    component: Collection,
    meta: { requiresAuth: true }
  },
  {
    path: '/upload',
    name: 'upload',
    component: Upload,
    meta: { requiresAuth: true }
  },
  {
    path: '/analysis/:asset_id',
    name: 'analysis',
    component: Analysis,
    meta: { requiresAuth: true }
  },
  {
    path: "/",
    name: "Login",
    component: Login,
    meta: { requiresAuth: false },
  }
]

const router = new VueRouter({
    mode: 'history',
    routes,
});

export default router;
