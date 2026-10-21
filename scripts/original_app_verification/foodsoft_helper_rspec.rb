require 'rspec'
require 'bigdecimal'
load ENV.fetch("TARGET_HELPER")

class ConvertingPrice
  attr_reader :supplier_order_unit,:group_order_unit
  def initialize
    @supplier_order_unit='kg';@group_order_unit='piece'
  end
  def convert_quantity(value,from,to)
    raise "incorrect origin unit" unless from=='kg'
    raise "incorrect group unit" unless to=='piece'
    BigDecimal(value.to_s)/BigDecimal('1.3')
  end
end
class TestOrder
  attr_reader :price,:group_orders_sum,:units_received,:units_billed,:units_to_order
  def initialize(branch,received_value:'1.7')
    @price=ConvertingPrice.new
    quantity=(BigDecimal('1.7')/BigDecimal('1.3'))
    @group_orders_sum={quantity:quantity}
    @units_received= branch==:received ? BigDecimal(received_value) : nil
    @units_to_order= branch==:ordered ? BigDecimal(received_value) : nil
    @units_billed= branch==:billed ? quantity : nil
  end
end
RSpec.describe 'Foodsoft original OrdersHelper source: quantity balancing' do
  let(:helper) { Object.new.extend(OrdersHelper) }
  [:ordered,:received].each do |branch|
    it "#{branch} equal 1.7kg versus (1.7/1.3) pieces does NOT flag" do
      expect(helper.ordered_quantities_different_from_group_orders?(TestOrder.new(branch))).to eq(false)
    end
    it "#{branch} definite difference continues to flag" do
      v=TestOrder.new(branch,received_value:'1.9')
      expect(helper.ordered_quantities_different_from_group_orders?(v)).to eq(branch==:ordered ? '!' : '?')
    end
  end
  it 'billed equal exact group units is not flagged' do
    expect(helper.ordered_quantities_different_from_group_orders?(TestOrder.new(:billed))).to eq(false)
  end
  it 'billed genuine difference is flagged' do
    o=TestOrder.new(:billed)
    o.instance_variable_set(:@units_billed,BigDecimal('1.6'))
    expect(helper.ordered_quantities_different_from_group_orders?(o)).to eq('?')
  end
  it 'empty quantities return nil' do
    expect(helper.ordered_quantities_different_from_group_orders?(TestOrder.new(:empty))).to eq(nil)
  end
  it 'genuine difference honors custom marker' do
    expect(helper.ordered_quantities_different_from_group_orders?(TestOrder.new(:ordered,received_value:'1.9'),'DIFF')).to eq('DIFF')
  end
  it 'preserves received branch precedence if received and ordered both exist' do
    o=TestOrder.new(:received)
    o.instance_variable_set(:@units_to_order,BigDecimal('1.9'))
    expect(helper.ordered_quantities_different_from_group_orders?(o)).to eq(false)
  end
end
