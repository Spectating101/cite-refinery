"use strict";
// Compile exact pinned upstream CoffeeScript, including its original Jasmine
// tests; upstream code is never committed or changed.
const fs=require('node:fs'),path=require('node:path');
const [source,spec,modules,scratch]=process.argv.slice(2);
if(!source||!spec||!modules||!scratch)throw Error('Expected original source, original spec, module path, temporary output');
const coffee=require(path.join(modules,'coffee-script'));
if(coffee.VERSION!=='1.12.7')throw Error('Unexpected original CoffeeScript compiler version');
fs.mkdirSync(scratch,{recursive:true});
for(const [target,orig] of [['service.js',source],['original_spec.js',spec]]){
 fs.writeFileSync(path.join(scratch,target),coffee.compile(fs.readFileSync(orig,'utf8'),{bare:true}));
}
fs.writeFileSync(path.join(scratch,'bootstrap.js'),
 "(function(){angular.module('admin.enterprises',[]).value('Enterprises',{geocodedEnterprises:function(){return [];}});angular.module('Darkswarm',['admin.enterprises']);})();\n");
