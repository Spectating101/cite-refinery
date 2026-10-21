"use strict";
const path=require('node:path');
const modules=process.env.CITE_VERIFY_NODE_MODULES;
const scratch=process.env.CITE_VERIFY_BROWSER_SCRATCH;
const extra=path.resolve(__dirname,'map_browser_regressions.js');
if(!modules||!scratch)throw Error('CITE_VERIFY_NODE_MODULES and CITE_VERIFY_BROWSER_SCRATCH must be specified');
module.exports=function(config){
 config.set({
  basePath:scratch,
  frameworks:['jasmine'],
  plugins:[require(path.join(modules,'karma-jasmine')),require(path.join(modules,'karma-chrome-launcher'))],
  files:[path.join(modules,'angular/angular.js'),path.join(modules,'angular-mocks/angular-mocks.js'),
         'bootstrap.js','service.js','original_spec.js',extra],
  browsers:['ChromeHeadlessNoSandbox'],
  customLaunchers:{ChromeHeadlessNoSandbox:{base:'ChromeHeadless',flags:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']}},
  singleRun:true,reporters:['dots'],colors:false,client:{clearContext:false},
  browserNoActivityTimeout:20000,logLevel:config.LOG_WARN,
 });
};
