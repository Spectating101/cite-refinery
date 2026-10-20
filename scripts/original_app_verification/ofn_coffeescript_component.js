// Reproduces actual pinned CoffeeScript source execution via compiler 1.12.7.
// No app server or browser is involved. Only this factory runs in isolated VM.
"use strict";
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const path=require('node:path');
const sourceFile=process.argv[2];
const coffeeModule=process.argv[3];
const candidate=process.argv[4]==='candidate';
if (!sourceFile||!coffeeModule) throw new Error('Usage: node script source.coffee pinned_coffee_package [candidate|original]');
const coffee=require(coffeeModule);
const source=fs.readFileSync(sourceFile,'utf8');
let moduleFactory=null;
const sandbox={
  Math,
  angular:{module(name){assert.equal(name,'Darkswarm');return{
     factory(name,callback){assert.equal(name,'MapCentreCalculator');moduleFactory=callback;}
  }}}
};
const compiled=coffee.compile(source,{bare:true});
vm.runInNewContext(compiled,sandbox,{timeout:1500,filename:'pinned_MapCentreCalculator.js'});
assert.equal(typeof moduleFactory,'function');
let fixtures=[];
const enterprises={geocodedEnterprises:()=>fixtures};
const config={open_street_map_default_latitude:76.26,open_street_map_default_longitude:-42.66};
const obj=moduleFactory(enterprises,config);
const checks=[];
function record(name,observed,expected){
 checks.push({name,actual:observed,expected,pass:Object.is(observed,expected)});
}
fixtures=[];
record('no_enterprises_configured_latitude',obj.initialLatitude(),76.26);
record('no_enterprises_configured_longitude',obj.initialLongitude(),-42.66);
fixtures=[{latitude:53,longitude:-6},{latitude:54,longitude:-7}];
record('existing_two_coordinate_latitude_case',obj.initialLatitude(),53.5);
record('existing_two_coordinate_longitude_case',obj.initialLongitude(),-6.5);
fixtures=[{latitude:49,longitude:-120},{latitude:51,longitude:-110},{latitude:53,longitude:-100}];
record('three_good_location_midpoint',obj.initialLatitude(),51);
fixtures=[...fixtures,{latitude:-15,longitude:-50}];
record('four_points_with_bad_geocode_actual_center',obj.initialLatitude(),
       candidate?50:19);
record('four_points_outlier_preserves_canada_region',obj.initialLatitude(),50);
record('ordinary_two_point_midpoint_positive_and_negative',
       obj._calculate('longitude',[{longitude:7},{longitude:-4}]),1.5);
// Adversarial geographic case: multiple bad coordinates defeat a naive median.
fixtures=[{latitude:49,longitude:-120},{latitude:51,longitude:-110},
          {latitude:53,longitude:-100},{latitude:-15,longitude:-50},
          {latitude:-14,longitude:-49},{latitude:-13,longitude:-48}];
const multiOutlierCenter=obj.initialLatitude();
record('three_misgeocodes_must_still_center_in_expected_country_region',
       multiOutlierCenter>=45&&multiOutlierCenter<=56,true);
const result={
  schema:'cite_refinery.pinned_ofn_component_execution.v1',
  original_coffeescript_runtime:'coffee-script@'+coffee.VERSION,
  upstream_source_compiled_and_executed:true,
  full_angular_app_executed:false,
  original_application_test_suite_executed:false,
  source_kind:candidate?'local_candidate_patch':'pinned_upstream',
  validations:checks,
  all_standard_regressions_pass:checks.filter(x=>!x.name.includes('outlier_preserves') && !x.name.includes('misgeocodes_must')).every(x=>x.pass),
  outlier_regression_pass:checks.find(x=>x.name==='four_points_outlier_preserves_canada_region').pass,
  multiple_outliers_regression_pass:checks.find(x=>x.name==='three_misgeocodes_must_still_center_in_expected_country_region').pass,
  zoom_and_geographic_bounds_integration_verified:false,
  bound:'Synthetic geocoordinates only. Map zoom, actual user records, map layer integration not exercised.'
};
process.stdout.write(JSON.stringify(result)+'\n');
