describe('MapCentreCalculator adversarial geographic integration cases', function () {
  var calc, enterprises, config;
  beforeEach(function () {
    angular.mock.module('Darkswarm');
    angular.mock.module('admin.enterprises');
    angular.module('Darkswarm').value('openStreetMapConfig',{
      open_street_map_default_latitude:51,
      open_street_map_default_longitude:-110,
      open_street_map_latitude_min:41,
      open_street_map_latitude_max:84,
      open_street_map_longitude_min:-141,
      open_street_map_longitude_max:-52
    });
    inject(function (_MapCentreCalculator_,_Enterprises_,_openStreetMapConfig_){
      calc=_MapCentreCalculator_;
      enterprises=_Enterprises_;
      config=_openStreetMapConfig_;
    });
  });
  it('keeps center in the country when a single geocode is outlying',function(){
    enterprises.geocodedEnterprises=function(){return [
      {latitude:49,longitude:-120},{latitude:51,longitude:-110},
      {latitude:53,longitude:-100},{latitude:-15,longitude:-50}
    ];};
    expect(calc.initialLatitude()).toBeGreaterThan(44);
    expect(calc.initialLatitude()).toBeLessThan(56);
  });
  it('retains a valid country center when multiple outliers exist',function(){
    enterprises.geocodedEnterprises=function(){return [
      {latitude:49,longitude:-120},{latitude:51,longitude:-110},
      {latitude:53,longitude:-100},{latitude:-15,longitude:-50},
      {latitude:-14,longitude:-49},{latitude:-13,longitude:-48}
    ];};
    expect(calc.initialLatitude()).toBeGreaterThan(44);
    expect(calc.initialLatitude()).toBeLessThan(56);
  });
  it('excludes invalid nonfinite coordinates from viewport math',function(){
    enterprises.geocodedEnterprises=function(){return [
      {latitude:49,longitude:-120},{latitude:NaN,longitude:NaN},
      {latitude:53,longitude:-100}
    ];};
    expect(Number.isFinite(calc.initialLatitude())).toBeTrue();
    expect(Number.isFinite(calc.initialLongitude())).toBeTrue();
  });
  it('uses a dateline-aware longitude midpoint for valid cross-antimeridian nodes',function(){
    delete config.open_street_map_latitude_min;
    delete config.open_street_map_latitude_max;
    delete config.open_street_map_longitude_min;
    delete config.open_street_map_longitude_max;
    enterprises.geocodedEnterprises=function(){return [
      {latitude:7,longitude:179},{latitude:7,longitude:-179}
    ];};
    expect(Math.abs(calc.initialLongitude())).toBeGreaterThan(170);
  });
  it('works with default configured center when no enterprises exist',function(){
    enterprises.geocodedEnterprises=function(){return [];};
    expect(calc.initialLatitude()).toEqual(51);
    expect(calc.initialLongitude()).toEqual(-110);
  });
});
