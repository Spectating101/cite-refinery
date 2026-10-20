# Execute original Foodsoft OrdersHelper without starting Rails or its DB.
# Ruby 3.3-alpine in a network-disabled read-only container.
require 'json'
require 'bigdecimal'
source=ARGV.fetch(0)
load source
class StubPrice
  attr_reader :supplier_order_unit,:group_order_unit
  def initialize
    @supplier_order_unit='kg'
    @group_order_unit='unit'
  end
  def convert_quantity(amount, _origin, _destination)
    amount.is_a?(BigDecimal) ? amount : BigDecimal(amount.to_s)
  end
end
class StubOrderArticle
  attr_reader :price,:group_orders_sum,:units_received,:units_billed,:units_to_order
  def initialize(branch, actual_quantity)
    @price=StubPrice.new
    @group_orders_sum={quantity:actual_quantity}
    @units_received=branch==:received ? actual_quantity : nil
    @units_billed=branch==:billed ? actual_quantity : nil
    @units_to_order=branch==:ordered ? actual_quantity : nil
  end
end
runner=Object.new.extend(OrdersHelper)
precision=BigDecimal('1.7')/BigDecimal('1.3')
different=BigDecimal('1.309')
cases=[]
def record(cases,name,branch,observed,expected)
  cases << {name:name,branch:branch.to_s,actual:observed,expected:expected,
            pass:observed==expected}
end
[:ordered,:received,:billed].each do |branch|
  # Original method rounds the converted order/received value to 3 places
  # but not the group order quantity; the billed branch compares raw values.
  same=StubOrderArticle.new(branch,precision)
  result=runner.ordered_quantities_different_from_group_orders?(same)
  record(cases,"equal_value_precision_#{branch}",branch,result,false)
end
# Verify changed quantity continues to flag a discrepancy, not hidden by fix.
[:ordered,:received,:billed].each do |branch|
  a=StubOrderArticle.new(branch,precision)
  a.instance_variable_set(:@group_orders_sum,{quantity:different})
  result=runner.ordered_quantities_different_from_group_orders?(a)
  expected= branch==:ordered ? '!' : '?'
  record(cases,"genuine_difference_#{branch}",branch,result,expected)
end
# Null cases yield nil when no quantities supplied.
empty=StubOrderArticle.new(:none,precision)
record(cases,'absent_quantities_nil',:none,
       runner.ordered_quantities_different_from_group_orders?(empty),nil)
report={
  schema:'cite_refinery.pinned_foodsoft_helper_execution.v1',
  ruby_version:RUBY_VERSION,
  upstream_ruby_helper_loaded_and_executed:true,
  rails_app_executed:false, rails_test_suite_executed:false,
  source_kind:ARGV[1]=='candidate' ? 'local_candidate_patch' : 'pinned_upstream',
  source:source,case_count:cases.length,
  validations:cases,
  equal_ordered_and_received_precision_regressions_pass:
    cases.select{|c|c[:name].start_with?('equal_value_precision') &&
       [:ordered,:received].include?(c[:branch].to_sym)}.all?{|c|c[:pass]},
  genuine_difference_regressions_pass:
    cases.select{|c|c[:name].start_with?('genuine_difference')}.all?{|c|c[:pass]},
  scope:'Original helper invoked with exact BigDecimal conversion stub; Rails models, database, app integration and UI not run.'
}
puts JSON.generate(report)
